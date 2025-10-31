#!/usr/bin/env python3
"""
Side-View Spectrogram Lines (PyQtGraph)
- Uses AudioAnalyzer to load audio + BPM (expects analyzer.y and analyzer.sr after load_audio()).
- Draws many frequency-band curves as a 2D side-view (time on x, amplitude on y, "depth" = different bands).
- Efficient: PyQtGraph + precomputed spectrogram + setData updates.
- 'Pick this frame' button appears only when paused; saves PNG next to the script and exits.

Dependencies: PyQt5, pyqtgraph, numpy
"""

import os, sys, time, math
import numpy as np

# --- Your analyzer ---
try:
    from extract_characteristics import AudioAnalyzer
except Exception as e:
    print("Error importing AudioAnalyzer:", e)
    raise

# --- Qt / PG ---
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

# Optional: image exporter for saving frames
try:
    import pyqtgraph.exporters as exporters
except Exception:
    exporters = None


# ---------------- Utilities ----------------
def hann(n):
    return 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))

def compute_band_spectrogram(y, sr, n_fft=2048, hop=512, n_bands=24, fmin=40.0, fmax=None):
    """
    Lightweight STFT -> magnitude -> collapse into n_bands on a perceptual-ish (log) scale.
    Returns:
        mags: (frames, n_bands) float32 in [0,1]
        times: (frames,) seconds
        band_edges_hz: (n_bands+1,) edges in Hz (log spaced)
    """
    if y.ndim > 1:  # stereo -> mono
        y = y.mean(axis=1)
    if fmax is None:
        fmax = min(sr * 0.5, 16000.0)

    # Pad so last frame is full-sized
    pad = n_fft - (len(y) % hop)
    if pad != n_fft:
        y = np.pad(y, (0, pad), mode="constant")

    win = hann(n_fft).astype(np.float32)
    n_frames = 1 + (len(y) - n_fft) // hop
    # FFT frequencies
    freqs = np.fft.rfftfreq(n_fft, d=1.0 / sr)

    # Log-spaced band edges
    edges = np.geomspace(max(1.0, fmin), max(fmin + 1.0, fmax), num=n_bands + 1)
    # Precompute index slices for each band
    band_idx = []
    for b in range(n_bands):
        f_lo, f_hi = edges[b], edges[b + 1]
        lo = np.searchsorted(freqs, f_lo, side="left")
        hi = np.searchsorted(freqs, f_hi, side="right")
        if hi <= lo:
            hi = min(len(freqs), lo + 1)
        band_idx.append((lo, hi))

    mags = np.zeros((n_frames, n_bands), dtype=np.float32)

    # Vectorized framing is memory heavy; stream/iterate to be light.
    pos = 0
    for i in range(n_frames):
        frame = y[pos : pos + n_fft]
        pos += hop
        spec = np.fft.rfft(frame * win, n=n_fft)
        mag = np.abs(spec)
        # Collapse to bands
        for b, (lo, hi) in enumerate(band_idx):
            # robust average (log-mean via exp(mean(log(x+eps))))
            band_slice = mag[lo:hi]
            if band_slice.size:
                mags[i, b] = float(np.mean(band_slice))
        # Optional simple compression for perceptual balance
    mags = np.asarray(mags)
    # Normalize across time per-band, then global normalize for [0,1]
    eps = 1e-8
    band_max = mags.max(axis=0, keepdims=True) + eps
    mags = mags / band_max
    gmax = mags.max() + eps
    mags = (mags / gmax).astype(np.float32)

    times = np.arange(n_frames) * (hop / sr)
    return mags, times, edges


def bpm_to_interval_ms(bpm, steps_per_beat=8, speed_mult=1.0):
    if bpm is None or bpm <= 0:
        bpm = 120.0
    base = 60_000.0 / (bpm * steps_per_beat)
    return int(max(5, base / max(1e-3, speed_mult)))


# -------------- Main Widget ----------------
class SideSpectroApp(QtWidgets.QMainWindow):
    def __init__(self, audio_path=None):
        super().__init__()
        self.setWindowTitle("Side-View Spectrogram Lines — PyQtGraph")
        self.resize(1100, 680)

        # State
        self.audio_path = audio_path
        self.analyzer = None
        self.y = None
        self.sr = None
        self.bpm = 120.0
        self.mags = None       # (frames, n_bands) in [0,1]
        self.times = None
        self.band_edges = None
        self.ptr = 0           # current time index for window start
        self.playing = True

        # Parameters (exposed in UI)
        self.n_bands = 24
        self.window_sec = 12.0
        self.steps_per_beat = 8
        self.speed_mult = 1.0
        self.curve_thickness = 2.0
        self.curve_spacing = 0.08  # vertical separation between bands
        self.morph_alpha = 0.25    # smoothing between frames (0..1)

        self._build_ui()
        if audio_path:
            self.load_audio(audio_path)
        self._start_timer()

    # -------- UI --------
    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Plot
        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget()
        # Keep the plot background black
        self.plot.setBackground("k")
        self.plot.showGrid(x=False, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        # Hide axes and labels so only the curves are visible on a black background.
        # Use PlotItem.hideAxis where available; fall back gracefully for different pyqtgraph versions.
        try:
            self.plot.plotItem.hideAxis('bottom')
            self.plot.plotItem.hideAxis('left')
        except Exception:
            try:
                self.plot.hideAxis('bottom')
                self.plot.hideAxis('left')
            except Exception:
                # Last resort: clear labels and make them invisible
                self.plot.setLabel("bottom", "", color="#000")
                self.plot.setLabel("left", "", color="#000")
        layout.addWidget(self.plot, 1)

        # Curves (created lazily once mags known)
        self.curves = []
        self.prev_frame = None

        # Controls
        controls = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(controls)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)
        layout.addWidget(controls)

        # Buttons
        self.load_btn = QtWidgets.QPushButton("Load Audio…")
        self.load_btn.clicked.connect(self._choose_audio)
        grid.addWidget(self.load_btn, 0, 0)

        self.play_btn = QtWidgets.QPushButton("⏸ Pause")
        self.play_btn.clicked.connect(self._toggle_play)
        grid.addWidget(self.play_btn, 0, 1)

        self.pick_btn = QtWidgets.QPushButton("Pick this frame")
        self.pick_btn.setVisible(False)
        self.pick_btn.clicked.connect(self._pick_frame_and_quit)
        grid.addWidget(self.pick_btn, 0, 2)

        # Sliders / spinboxes
        def add_labeled(row, label, widget):
            lab = QtWidgets.QLabel(label)
            lab.setStyleSheet("color:#DDD;")
            grid.addWidget(lab, row, 0)
            grid.addWidget(widget, row, 1, 1, 2)

        self.bands_spin = QtWidgets.QSpinBox()
        self.bands_spin.setRange(4, 96)
        self.bands_spin.setValue(self.n_bands)
        self.bands_spin.valueChanged.connect(self._rebuild_bands)
        add_labeled(1, "Bands (depth):", self.bands_spin)

        self.window_spin = QtWidgets.QDoubleSpinBox()
        self.window_spin.setDecimals(1)
        self.window_spin.setRange(4.0, 60.0)
        self.window_spin.setValue(self.window_sec)
        self.window_spin.valueChanged.connect(self._set_window)
        add_labeled(2, "Time window (s):", self.window_spin)

        self.spb_spin = QtWidgets.QSpinBox()
        self.spb_spin.setRange(1, 32)
        self.spb_spin.setValue(self.steps_per_beat)
        self.spb_spin.valueChanged.connect(self._set_spb)
        add_labeled(3, "Steps per beat:", self.spb_spin)

        self.speed_spin = QtWidgets.QDoubleSpinBox()
        self.speed_spin.setRange(0.25, 8.0); self.speed_spin.setSingleStep(0.25)
        self.speed_spin.setValue(self.speed_mult)
        self.speed_spin.valueChanged.connect(self._set_speed)
        add_labeled(4, "Speed ×:", self.speed_spin)

        self.thick_spin = QtWidgets.QDoubleSpinBox()
        self.thick_spin.setRange(1.0, 6.0); self.thick_spin.setSingleStep(0.5)
        self.thick_spin.setValue(self.curve_thickness)
        self.thick_spin.valueChanged.connect(self._set_thickness)
        add_labeled(5, "Line thickness:", self.thick_spin)

        self.spacing_spin = QtWidgets.QDoubleSpinBox()
        self.spacing_spin.setRange(0.02, 0.3); self.spacing_spin.setSingleStep(0.01)
        self.spacing_spin.setValue(self.curve_spacing)
        self.spacing_spin.valueChanged.connect(self._set_spacing)
        add_labeled(6, "Band spacing:", self.spacing_spin)

        self.morph_spin = QtWidgets.QDoubleSpinBox()
        self.morph_spin.setRange(0.0, 1.0); self.morph_spin.setSingleStep(0.05)
        self.morph_spin.setValue(self.morph_alpha)
        self.morph_spin.valueChanged.connect(self._set_morph)
        add_labeled(7, "Morph smoothing:", self.morph_spin)

        # Dark labels
        controls.setStyleSheet("""
            QWidget { background:#111; }
            QPushButton { color:#EEE; background:#222; border: 1px solid #333; padding:6px 10px; }
            QPushButton:hover { background:#2d2d2d; }
            QDoubleSpinBox, QSpinBox { color:#EEE; background:#222; border:1px solid #333; }
            QLabel { color:#CCC; }
        """)

    # -------- Data / Analyzer --------
    def load_audio(self, path):
        self.audio_path = path
        self.setWindowTitle(f"Side-View Spectrogram Lines — {os.path.basename(path)}")
        self.analyzer = AudioAnalyzer(path)
        self.analyzer.load_audio()
        # BPM if available
        try:
            self.analyzer.analyze_tempo()
            # Try common places the user has used before
            bpm = None
            if hasattr(self.analyzer, "features"):
                if "bpm" in self.analyzer.features:
                    bpm = float(self.analyzer.features["bpm"])
                elif "tempo" in self.analyzer.features and isinstance(self.analyzer.features["tempo"], dict):
                    bpm = float(self.analyzer.features["tempo"].get("bpm", 120))
            if hasattr(self.analyzer, "summarize"):
                try:
                    s = self.analyzer.summarize()
                    if "bpm" in s:
                        bpm = float(s["bpm"])
                except Exception:
                    pass
            self.bpm = float(bpm) if bpm and bpm > 0 else 120.0
        except Exception:
            self.bpm = 120.0  # fallback

        # Raw audio (expects analyzer to expose y / sr; adapt if different)
        self.y = getattr(self.analyzer, "y", None)
        self.sr = getattr(self.analyzer, "sr", None)
        if self.y is None or self.sr is None:
            raise RuntimeError("AudioAnalyzer must expose waveform as .y and sample rate as .sr after load_audio().")

        # Compute spectrogram bands
        self.mags, self.times, self.band_edges = compute_band_spectrogram(
            self.y, self.sr, n_fft=2048, hop=512, n_bands=self.n_bands
        )

        # Build curves now that we know lengths
        self._create_curves()
        self.ptr = 0
        self.prev_frame = None
        self._update_plot(force=True)

    # -------- Curves / Rendering --------
    def _create_curves(self):
        self.plot.clear()
        self.curves = []

        # X axis is rolling window of time
        self.window_sec = float(self.window_spin.value())
        # dummy x initialized; updated every frame
        x = np.linspace(0, self.window_sec, int(self.window_sec * 60) + 10)

        # Choose a pleasant progression of hues by alpha per band (near-white)
        for b in range(self.n_bands):
            pen = pg.mkPen((235, 235, 235, int(220 - 180 * (b / max(1, self.n_bands - 1)))) ,
                           width=self.curve_thickness)
            curve = self.plot.plot(x, np.zeros_like(x), pen=pen, antialias=True)
            self.curves.append(curve)

        # Adjust view
        self.plot.setXRange(0, self.window_sec)
        # Dynamic Y range: stack bands upward with spacing; normalized magnitude in [0,1]
        y_top = self.n_bands * self.curve_spacing + 1.0
        self.plot.setYRange(-0.2, y_top)

    def _rolling_window_data(self, frame_idx):
        """
        Returns x vector (window_sec length) and a list of y vectors for each band,
        where each band's baseline is vertically offset by band index * spacing,
        and the magnitude envelope rides on top (with mild temporal smoothing).
        """
        if self.mags is None or self.times is None:
            return None, None

        n_frames = len(self.times)
        if n_frames < 2:
            return None, None

        dt = self.times[1] - self.times[0]
        win_frames = max(4, int(self.window_sec / max(dt, 1e-9)))

        # Window bounds (end is exclusive)
        end = max(1, min(n_frames, int(frame_idx)))
        start = max(0, end - win_frames)

        # Slice current window (can be empty at the very beginning)
        t = self.times[start:end]
        m = self.mags[start:end, :] if end > start else np.empty((0, self.n_bands), dtype=np.float32)

        # Left pad if not enough frames yet (e.g., at startup)
        cur = m.shape[0]
        if cur < win_frames:
            pad = win_frames - cur
            # time padding goes negative back in steps of dt
            t_pad = np.linspace(-pad * dt, -dt, pad, dtype=float)
            m_pad = np.zeros((pad, self.n_bands), dtype=np.float32)
            if cur:
                t = np.concatenate([t_pad, t])
                m = np.vstack([m_pad, m])
            else:
                # no real frames yet; the window is fully padded
                t = t_pad
                m = m_pad

        # Now shift time so window starts at 0
        if t.size:
            t = t - t.min()

        # Temporal smoothing for nicer morph (blend last row vs previous)
        if self.prev_frame is not None and m.shape[0] > 0:
            m[-1, :] = (1.0 - self.morph_alpha) * self.prev_frame + self.morph_alpha * m[-1, :]
        if m.shape[0] > 0:
            self.prev_frame = m[-1, :].copy()

        # Build per-band y values with offsets
        ys = []
        for b in range(self.n_bands):
            baseline = (b + 1) * self.curve_spacing
            ys.append(baseline + m[:, b])

        return t, ys


    def _update_plot(self, force=False):
        if self.mags is None:
            return
        x, ys = self._rolling_window_data(self.ptr)
        if x is None or ys is None or x.size == 0:
            return

        # Update curves (ensure length match)
        for b, curve in enumerate(self.curves):
            if b < len(ys):
                yb = ys[b]
                if yb is not None and yb.shape[0] == x.shape[0]:
                    curve.setData(x, yb)

        # Axes ranges
        self.plot.setXRange(0, max(self.window_sec, float(x.max())), padding=0)

    # -------- Timer & playback --------
    def _start_timer(self):
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self._retime()

    def _retime(self):
        ms = bpm_to_interval_ms(self.bpm, self.steps_per_beat, self.speed_mult)
        self.timer.start(ms)

    def _on_tick(self):
        if not self.playing or self.mags is None:
            return
        self.ptr = min(len(self.times) - 1, self.ptr + 1)
        self._update_plot()
        if self.ptr >= len(self.times) - 1:
            self.playing = False
            self.play_btn.setText("▶️ Play")
            self.pick_btn.setVisible(True)

    # -------- Controls callbacks --------
    def _choose_audio(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose audio file", "", "Audio Files (*.wav *.mp3 *.flac *.aiff *.aif *.ogg);;All Files (*)")
        if path:
            self.load_audio(path)

    def _toggle_play(self):
        self.playing = not self.playing
        self.play_btn.setText("⏸ Pause" if self.playing else "▶️ Play")
        self.pick_btn.setVisible(not self.playing)

    def _pick_frame_and_quit(self):
        # Save current plot as PNG in script directory
        ts = time.strftime("%Y%m%d-%H%M%S")
        base = os.path.splitext(os.path.basename(self.audio_path or "frame"))[0]
        fname = f"{base}_sideSpectro_{ts}.png"
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)

        if exporters is not None:
            exp = exporters.ImageExporter(self.plot.plotItem)
            exp.parameters()["width"] = 2400  # bigger export
            exp.export(out_path)
        else:
            # Fallback: grab the widget (lower fidelity)
            pix = self.plot.grab()
            pix.save(out_path, "PNG")

        print(f"saved as {fname}")
        QtWidgets.qApp.quit()

    def _rebuild_bands(self, val):
        self.n_bands = int(val)
        if self.y is not None:
            # recompute bands at same positions
            self.mags, self.times, self.band_edges = compute_band_spectrogram(
                self.y, self.sr, n_fft=2048, hop=512, n_bands=self.n_bands
            )
            self._create_curves()
            self.ptr = 0
            self.prev_frame = None
            self._update_plot(force=True)

    def _set_window(self, v):
        self.window_sec = float(v)
        if self.curves:
            self._create_curves()

    def _set_spb(self, v):
        self.steps_per_beat = int(v)
        self._retime()

    def _set_speed(self, v):
        self.speed_mult = float(v)
        self._retime()

    def _set_thickness(self, v):
        self.curve_thickness = float(v)
        for c in self.curves:
            pen = c.opts["pen"]
            pen.setWidthF(self.curve_thickness)
            c.setPen(pen)

    def _set_spacing(self, v):
        self.curve_spacing = float(v)
        if self.curves:
            self._create_curves()

    def _set_morph(self, v):
        self.morph_alpha = float(v)


# -------------- Entrypoint --------------
def main(audio_path=None):
    """
    Unified entry point that works with:
      - launcher-provided main(audio_path)
      - CLI: python script.py /path/to/file.wav
      - CLI: python script.py --audio /path/to/file.wav
      - Environment variable: AUDIO_PATH
    """
    import argparse, os, sys
    from PyQt5 import QtWidgets

    # Parse CLI args safely (ignore unknown ones)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("audio", nargs="?", default=None)
    parser.add_argument("--audio", dest="audio_kw", default=None)
    args, _ = parser.parse_known_args()

    # Resolve final path: direct arg > CLI args > env var
    audio_path = audio_path or args.audio_kw or args.audio or os.getenv("AUDIO_PATH")

    app = QtWidgets.QApplication(sys.argv)
    w = SideSpectroApp(audio_path)
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
