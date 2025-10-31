"""
Static Moving Waves - Tkinter + Matplotlib (real-time sliders)
"""

import os
import sys
import argparse
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import random

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()
if HERE not in sys.path:
    sys.path.append(HERE)
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

try:
    from extract_characteristics import AudioAnalyzer
except Exception as e:
    print("Error importing AudioAnalyzer from extract_characteristics.py:", e)
    raise

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle

NOTE_TO_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
}

def parse_key_feature(key_feat):
    def parse_one(obj):
        if isinstance(obj, dict):
            tonic = obj.get("key") or obj.get("tonic") or obj.get("note") or "C"
            strength = float(obj.get("strength", obj.get("score", 1.0)))
            return tonic, strength
        if isinstance(obj, str):
            s = obj.strip()
            m = re.match(r"^\s*([A-Ga-g])([#bB]?)", s)
            if m:
                letter = m.group(1).upper()
                accidental = m.group(2).replace('B','b')
                return (letter + accidental), 1.0
            return "C", 1.0
        return "C", 1.0

    cand = []
    if isinstance(key_feat, dict):
        if "candidates" in key_feat and isinstance(key_feat["candidates"], (list, tuple)):
            for c in key_feat["candidates"]:
                cand.append(parse_one(c))
        else:
            cand.append(parse_one(key_feat))
    elif isinstance(key_feat, (list, tuple)):
        for x in key_feat:
            cand.append(parse_one(x))
    elif isinstance(key_feat, str):
        cand.append(parse_one(key_feat))
    else:
        cand.append(("C", 1.0))

    strengths = np.array([max(0.0, float(s)) for _, s in cand], dtype=float)
    if strengths.sum() <= 1e-12:
        strengths = np.linspace(1.0, 0.2, num=len(cand))
    strengths = strengths / (strengths.max() if strengths.max() > 0 else 1.0)
    cand = [(cand[i][0], float(strengths[i])) for i in range(len(cand))]
    cand.sort(key=lambda kv: kv[1], reverse=True)
    return cand[:5]

# put near the top of the file (or inside the class if you prefer)
def center_and_raise(win):
    win.update_idletasks()
    w = win.winfo_width() or 800
    h = win.winfo_height() or 450
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = int((sw - w) / 2)
    y = int((sh - h) / 3)
    win.geometry(f"{w}x{h}+{x}+{y}")
    # bring to front briefly
    try:
        win.lift()
        win.attributes("-topmost", True)
        win.after(250, lambda: win.attributes("-topmost", False))
        win.focus_force()
    except Exception:
        pass


def tonic_to_visfreq(tonic):
    tonic = tonic.strip().title()
    if tonic not in NOTE_TO_SEMITONE:
        return 3.0
    semitone = NOTE_TO_SEMITONE[tonic]
    return 2.0 + (semitone / 11.0) * 4.0

def smooth_noise(n, seed=0, smooth=25):
    rng = np.random.default_rng(seed)
    y = rng.normal(0, 1, size=n)
    k = max(1, int(smooth))
    kernel = np.ones(k) / k
    z = np.convolve(y, kernel, mode="same")
    return z

class StaticWavesApp:
    def __init__(self, root, audio_path: str, fps: int = 30):
        self.root = root
        self.root.title(f"Visualisation of {os.path.basename(audio_path)}")
        # Keyboard shortcut: P to pick current frame
        self.root.bind("<p>", lambda _e: self._pick_this_frame())
        self.root.bind("<P>", lambda _e: self._pick_this_frame())
        self.audio_path = audio_path
        self.fps = int(fps)

        self.playing = True
        self.t = 0.0
        self.seed = random.randrange(0, 10_000)

        self.master_amp  = tk.DoubleVar(self.root, value=1.0)
        self.speed_mult  = tk.DoubleVar(self.root, value=1.0)
        self.density_mult= tk.DoubleVar(self.root, value=1.0)
        self.wobble      = tk.DoubleVar(self.root, value=0.25)
        self.diffusion   = tk.DoubleVar(self.root, value=0.0)  # 0 = off, 1 = strong glow



        self._load_features()
        self._build_ui()
        self._prepare_static_geometry()
        self._schedule_next_frame()

    def _load_features(self):
        analyzer = AudioAnalyzer(self.audio_path)
        analyzer.load_audio()
        analyzer.analyze_tempo()
        analyzer.analyze_key()
        analyzer.compute_loudness()

        tempo_feat = getattr(analyzer, "features", {}).get("bpm", {})
        try:
            self.bpm = int(tempo_feat) if tempo_feat else 120.0
        except Exception:
            self.bpm = 120.0

        key_feat = getattr(analyzer, "features", {}).get("key", {})
        self.key_candidates = parse_key_feature(key_feat) or [("C", 1.0)]
        while len(self.key_candidates) < 5:
            self.key_candidates.append(("C", self.key_candidates[-1][1]*0.7))

                # 1) Get spectral bands
        try:
            analyzer.compute_spectral_bands()
            bands = getattr(analyzer, "features", {}).get("bands", None)
        except Exception:
            bands = None

        # 2) Compute a contrast metric in [0,1] from bass/mids/treble
        wobble_init = None
        if bands is not None and all(k in bands for k in ("bass", "mids", "treble")):
            import numpy as np

            bass  = np.asarray(bands["bass"],  dtype=float)
            mids  = np.asarray(bands["mids"],  dtype=float)
            trebl = np.asarray(bands["treble"], dtype=float)
            n = min(bass.size, mids.size, trebl.size)

            if n > 10:
                bass, mids, trebl = bass[:n], mids[:n], trebl[:n]

                # --- Robust per-band normalization (5–95th percentile)
                def rnorm(x):
                    lo, hi = np.percentile(x, 5), np.percentile(x, 95)
                    rng = hi - lo if hi > lo else 1.0
                    return np.clip((x - lo) / rng, 0.0, 1.0)

                bN, mN, tN = rnorm(bass), rnorm(mids), rnorm(trebl)

                # --- Contrast metric: average pairwise absolute differences
                # per frame, then take median across time for stability
                d1 = np.abs(bN - mN)
                d2 = np.abs(mN - tN)
                d3 = np.abs(tN - bN)
                contrast_series = (d1 + d2 + d3) / 3.0
                contrast = float(np.median(contrast_series))  # 0..1

                # Map to an initial wobble (tweak scale/offset as you like)
                wobble_init = np.clip(0.15 + 0.85 * contrast, 0.0, 1.0)  # 0.15..1.0

        # 3) Apply it if computed
        if wobble_init is not None:
            try:
                self.wobble.set(float(wobble_init))
            except Exception:
                pass
        
        loud = analyzer.features.get("loudness", {})
        rms_db = np.asarray(loud.get("rms_db", []), dtype=float)

        if rms_db.size == 0 or np.all(np.isnan(rms_db)):
            # safe fallback if analysis fails
            self._loudness_norm_series = np.array([0.0], dtype=float)
        else:
            # normalize robustly to [0,1]
            valid = ~np.isnan(rms_db)
            if valid.any():
                lo = float(np.min(rms_db[valid]))
                hi = float(np.max(rms_db[valid]))
                rng = hi - lo if hi > lo else 1.0
                loud_norm = (rms_db - lo) / rng
                loud_norm[~valid] = 0.0
            else:
                loud_norm = np.zeros_like(rms_db, dtype=float)

            self._loudness_norm_series = loud_norm

        # initial base value for the slider from the first frame
        self._loudness_base = float(self._loudness_norm_series[0])

    def _build_ui(self):
        # Ensure diffusion var exists and is seeded from loudness base (0..1)
        import tkinter as tk
        from tkinter import ttk

        if not hasattr(self, "diffusion"):
            self.diffusion = tk.DoubleVar(value=getattr(self, "_loudness_base", 0.0))
        else:
            # Always reset to the loudness-seeded base when rebuilding UI
            self.diffusion.set(getattr(self, "_loudness_base", 0.0))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(9, 4.5), dpi=100, facecolor="black")
        self.ax = self.fig.add_subplot(111, facecolor="black")
        self.ax.set_xticks([]); self.ax.set_yticks([])
        self.ax.set_xlim(0, 1); self.ax.set_ylim(-1.2, 1.2)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=0, column=0, sticky="nsew")

        panel = ttk.Frame(self.root, padding=8)
        panel.grid(row=1, column=0, sticky="ew")
        for c in range(5): panel.columnconfigure(c, weight=1)

        self.play_btn = ttk.Button(panel, text="⏸ Pause", command=self._toggle_play)
        self.play_btn.grid(row=0, column=0, sticky="w")

        ttk.Label(panel, text=f"BPM (read): {self.bpm:.1f}").grid(row=0, column=1, sticky="w")
        ttk.Label(panel, text="Speed ×").grid(row=0, column=2, sticky="e")
        self.speed_entry = ttk.Scale(
            panel, from_=0.1, to=5.0, variable=self.speed_mult, orient="horizontal",
            command=lambda _e: self._on_param_change("speed")
        )
        self.speed_entry.grid(row=0, column=3, sticky="ew", padx=(6,0))

        ttk.Label(panel, text="Amplitude").grid(row=1, column=0, sticky="e")
        self.amp_entry = ttk.Scale(
            panel, from_=0.1, to=3.0, variable=self.master_amp, orient="horizontal",
            command=lambda v: (self.master_amp.set(float(v)), self._on_param_change("amp"))
        )
        self.amp_entry.grid(row=1, column=1, sticky="ew", padx=(6,0))

        ttk.Label(panel, text="Wobble").grid(row=2, column=0, sticky="e")
        self.wobble_entry = ttk.Scale(
            panel, from_=0.0, to=1.0, variable=self.wobble, orient="horizontal",
            command=lambda _e: self._on_param_change("wobble")
        )
        self.wobble_entry.grid(row=2, column=1, sticky="ew", padx=(6,0))

        ttk.Label(panel, text="Time").grid(row=2, column=2, sticky="e")
        self.time_scale = ttk.Scale(panel, from_=0.0, to=100.0, orient="horizontal", command=self._on_time_scrub)
        self.time_scale.grid(row=2, column=3, sticky="ew", padx=(6,0))

        # Diffusion seeded ONLY from loudness (RMS dB → normalized 0..1 in _load_data)
        ttk.Label(panel, text="Diffusion").grid(row=1, column=2, sticky="e")
        self.diffusion_entry = ttk.Scale(
            panel, from_=0.0, to=1.0, variable=self.diffusion, orient="horizontal",
            command=lambda v: (self.diffusion.set(float(v)), self._on_param_change("diffusion"))
        )
        self.diffusion_entry.grid(row=1, column=3, sticky="ew", padx=(6,0))

        # 'Pick this frame' button (always visible; disabled while playing)
        self.pick_btn = ttk.Button(panel, text="Pick this frame", command=self._pick_this_frame)
        self.pick_btn.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(8,0))
        self.pick_btn.state(['disabled'])

        self.lines = []
        for i in range(5):
            (ln,) = self.ax.plot([], [], color="white", alpha=0.35+0.12*i, linewidth=1.2+0.3*i)
            self.lines.append(ln)
        
        # Halos (soft glow) drawn underneath main lines
        self.halo_lines = []  # list of lists: one halo stack per layer
        halo_widths = [6.0, 12.0, 20.0]     # progressively wider strokes
        halo_alphas = [0.12, 0.06, 0.03]    # base alpha for each ring

        for i in range(5):
            layer_halos = []
            for w, a in zip(halo_widths, halo_alphas):
                (hln,) = self.ax.plot([], [], color="white",
                                    linewidth=w, alpha=0.0,   # start invisible
                                    zorder=1)                 # below main lines
                layer_halos.append((hln, w, a))
            self.halo_lines.append(layer_halos)

        # Make sure main lines sit on top
        for ln in self.lines:
            ln.set_zorder(2)

        # Slider controls (amp only when paused, speed only when playing)
        self._apply_control_states()


    def _prepare_static_geometry(self):
        base_density = 800
        density = int(base_density * (self.bpm/120.0) * float(self.density_mult.get()))
        density = int(np.clip(density, 300, 4000))

        self.x = np.linspace(0.0, 1.0, density)
        self.noise = smooth_noise(density, seed=self.seed, smooth=max(15, density//60))

        self.layer_cfg = []
        import math
        for idx in range(5):
            tonic, strength = self.key_candidates[idx] if idx < len(self.key_candidates) else ("C", 0.0)
            vis_f = 2.0 + (NOTE_TO_SEMITONE.get(tonic.strip().title(), 0) / 11.0) * 4.0
            phi = 2*math.pi*random.random()
            self.layer_cfg.append(dict(tonic=tonic, strength=float(strength), vis_freq=vis_f, phase=phi))

    def _compose_layer(self, cfg, tval):
        move_speed = 2.0 * float(self.speed_mult.get())
        base = np.sin(2*np.pi*(cfg["vis_freq"]*self.x - 0.15*move_speed*tval) + cfg["phase"])
        harm = 0.35*np.sin(2*np.pi*((cfg["vis_freq"]*2.2)*self.x + 0.07*move_speed*tval) + 0.7*cfg["phase"])
        wob = float(self.wobble.get())
        warped = np.sin(2*np.pi*(cfg["vis_freq"]*self.x + wob*self.noise*0.6 - 0.10*move_speed*tval) + cfg["phase"]*1.2)
        y = 0.6*base + 0.3*harm + 0.4*warped
        y *= cfg["strength"] * float(self.master_amp.get())
        return y

    def _schedule_next_frame(self):
        self.root.after(int(1000/self.fps), self._tick)

    def _tick(self):
        if self.playing:
            self.t += 0.033 * 2.0 * float(self.speed_mult.get())
            self.time_scale.set(self.t % 100.0)
            self._refresh()
        self._schedule_next_frame()

    def _on_param_change(self, which):
        if which == "density":
            self._prepare_static_geometry()
        self._refresh()

    def _refresh(self):
    # Read diffusion amount (0..1). If the attr isn't set yet, fall back to 0.
        diff = 0.0
        try:
            diff = float(self.diffusion.get())
        except Exception:
            pass

        for i, ln in enumerate(self.lines):
            if i < len(self.layer_cfg):
                # Compose waveform for this layer
                y = self._compose_layer(self.layer_cfg[i], self.t)
                ln.set_data(self.x, y)

                # --- Diffusion halos (soft glow) ---
                # If halos were created in _build_ui as self.halo_lines,
                # update them to mirror the main line with low alpha.
                if hasattr(self, "halo_lines") and i < len(self.halo_lines):
                    for (hln, w, a) in self.halo_lines[i]:
                        if diff > 0.0:
                            hln.set_data(self.x, y)       # same geometry as main line
                            hln.set_alpha(a * diff)       # fade with slider
                            # Optional: make halo width breathe with amplitude
                            # hln.set_linewidth(w * (0.8 + 0.2*float(self.master_amp.get())))
                        else:
                            hln.set_alpha(0.0)
                            hln.set_data([], [])
            else:
                # Hide any extra main lines
                ln.set_data([], [])
                # Hide any extra halos
                if hasattr(self, "halo_lines") and i < len(self.halo_lines):
                    for (hln, *_ ) in self.halo_lines[i]:
                        hln.set_alpha(0.0)
                        hln.set_data([], [])

        # Y-limits behavior (your existing logic)
        if self.playing:
            self.ax.set_ylim(-1.2 * float(self.master_amp.get()),
                            1.2 * float(self.master_amp.get()))
        else:
            self.ax.set_ylim(-1.2, 1.2)

        # Global BPM pulse (if you add a pulse_rect overlay elsewhere)
        bpm_hz = max(0.1, float(self.bpm) / 60.0)
        pulse = 0.5 + 0.5 * np.sin(2*np.pi * bpm_hz * self.t)
        alpha = 0.05 + 0.20 * pulse
        try:
            if hasattr(self, 'pulse_rect'):
                self.pulse_rect.set_alpha(alpha)
        except Exception:
            pass

        # Synchronous redraw so paused changes appear immediately
        self.canvas.draw()

        


    def _toggle_play(self):
        self.playing = not self.playing
        self._apply_control_states()
        self.play_btn.config(text="▶ Play" if not self.playing else "⏸ Pause")

        # Enable the 'Pick this frame' button when paused; disable when playing
        try:
            if hasattr(self, 'pick_btn'):
                if not self.playing:
                    self.pick_btn.state(['!disabled'])
                else:
                    self.pick_btn.state(['disabled'])
        except Exception:
            pass


    def _apply_control_states(self):
        if self.playing:
            # Playing: Speed enabled, Amplitude disabled
            try:
                self.speed_entry.state(['!disabled'])
                self.amp_entry.state(['disabled'])
            except Exception:
                # Fallback if not ttk
                self.speed_entry.configure(state='normal')
                self.amp_entry.configure(state='disabled')
        else:
            # Paused: Amplitude enabled, Speed disabled
            try:
                self.speed_entry.state(['disabled'])
                self.amp_entry.state(['!disabled'])
            except Exception:
                self.speed_entry.configure(state='disabled')
                self.amp_entry.configure(state='normal')

    def _pick_this_frame(self):
        """Save current frame as PNG in the same folder as this script, close GUI, and print the filename."""
        try:
            safe_t = f"{float(self.t):06.2f}".replace('.', '_')
            fname = f"staticwaves_{safe_t}.png"
        except Exception:
            fname = "staticwaves_frame.png"
        try:
            out_dir = HERE if 'HERE' in globals() else os.getcwd()
            fpath = os.path.join(out_dir, fname)
            self.fig.savefig(fpath, dpi=300, facecolor=self.fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
            print(f"saved as {fname}")
        except Exception as e:
            print(f"Failed to save frame: {e}")
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass

    def _reseed(self):
        self.seed = random.randrange(0, 10_000)
        self._prepare_static_geometry()
        self._refresh()

    def _on_time_scrub(self, _e=None):
        try:
            self.t = float(self.time_scale.get())
        except Exception:
            return
        if not self.playing:
            self._refresh()

def main():
    import argparse, os, sys
    # IMPORTANT: be tolerant of extra flags -> parse_known_args()
    parser = argparse.ArgumentParser(
        description="Static Moving Waves (Tk + Matplotlib)", add_help=True
    )
    parser.add_argument("audio", nargs="?", help="Path to audio file (wav, mp3, etc.)")
    parser.add_argument("--audio", dest="audio_kw", help="Path to audio file (alt flag)")
    parser.add_argument("--fps", type=int, default=30, help="Animation FPS (default: 30)")
    args, _unknown = parser.parse_known_args()

    # Resolve: --audio > positional > env var
    audio_path = args.audio_kw or args.audio or os.getenv("AUDIO_PATH")

    if not audio_path:
        root = tk.Tk(); root.withdraw()
        audio_path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[("Audio Files", "*.wav *.mp3 *.flac *.ogg *.m4a"), ("All Files", "*.*")]
        )
        if not audio_path:
            messagebox.showerror("No file selected", "You must choose an audio file.")
            return

    if not os.path.exists(audio_path):
        print(f"Audio file not found: {audio_path}")
        return

    root = tk.Tk()
    app = StaticWavesApp(root, audio_path=audio_path, fps=args.fps)

    root = tk.Tk()
    root.withdraw()  # avoid flashing at 0,0 while we build
    app = StaticWavesApp(root, audio_path=audio_path, fps=args.fps)

    # center & raise before showing
    def _show():
        center_and_raise(root)
        root.deiconify()
    root.after(50, _show)

    root.mainloop()



if __name__ == "__main__":
    main()