import librosa
import numpy as np
import pandas as pd
import json
import os

class AudioAnalyzer:
    """
    Analyze a .wav audio file and extract features useful for visualization:
      - BPM (tempo)
      - Musical key
      - Frequency band energies (bass, mids, treble)
      - Loudness (RMS in dB)

    Usage:
        analyzer = AudioAnalyzer("path/to/audio.wav")
        analyzer.load_audio()
        analyzer.analyze_tempo()
        analyzer.analyze_key()
        analyzer.compute_spectral_bands()
        analyzer.compute_loudness()
        data = analyzer.export_json("analysis.json")
    """

    def __init__(self, filepath, sr=44100, hop_length=512):
        if not filepath.lower().endswith(".wav"):
            raise ValueError("AudioAnalyzer only accepts .wav files.")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        self.filepath = filepath
        self.sr = sr
        self.hop_length = hop_length
        self.y = None
        self.duration = None
        self.features = {}

    def load_audio(self):
        """Load the .wav file as mono for analysis."""
        self.y, self.sr = librosa.load(self.filepath, sr=self.sr, mono=True)
        self.duration = librosa.get_duration(y=self.y, sr=self.sr)
        print(f"Loaded '{self.filepath}' ({self.duration:.2f}s @ {self.sr}Hz)")

    def analyze_tempo(self):
        """Detect global BPM and beat timestamps."""
        onset_env = librosa.onset.onset_strength(y=self.y, sr=self.sr, hop_length=self.hop_length)
        tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=self.sr, hop_length=self.hop_length)
        self.features["bpm"] = float(tempo)
        self.features["beats"] = librosa.frames_to_time(beats, sr=self.sr, hop_length=self.hop_length).tolist()

    def analyze_key(self):
        """Estimate the key using chroma features."""
        chroma = librosa.feature.chroma_cqt(y=self.y, sr=self.sr)
        chroma_mean = chroma.mean(axis=1)
        note_names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        key_index = chroma_mean.argmax()
        self.features["key"] = note_names[key_index]
        self.features["chroma"] = chroma_mean.tolist()

    def compute_spectral_bands(self):
        """Compute normalized average energy in bass, mids, and treble bands per frame."""
        S = np.abs(librosa.stft(self.y, n_fft=2048, hop_length=self.hop_length))
        freqs = librosa.fft_frequencies(sr=self.sr, n_fft=2048)
        bands = {
            "bass": (20, 150),
            "mids": (150, 2000),
            "treble": (2000, 8000)
        }

        band_energies = {}
        for name, (low, high) in bands.items():
            idx = np.where((freqs >= low) & (freqs < high))[0]
            energy = S[idx, :].mean(axis=0)
            v_norm = (energy - energy.min()) / (energy.max() - energy.min() + 1e-9)
            band_energies[name] = v_norm

        times = librosa.frames_to_time(np.arange(S.shape[1]), sr=self.sr, hop_length=self.hop_length)
        df = pd.DataFrame({
            "time": times,
            "bass": band_energies["bass"],
            "mids": band_energies["mids"],
            "treble": band_energies["treble"],
        })
        self.features["bands"] = df

    def compute_loudness(self):
        """Compute RMS loudness per frame (in dB)."""
        rms = librosa.feature.rms(y=self.y, hop_length=self.hop_length)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        times = librosa.frames_to_time(np.arange(len(rms)), sr=self.sr, hop_length=self.hop_length)
        df = pd.DataFrame({"time": times, "rms_db": rms_db})
        self.features["loudness"] = df

    def summarize(self):
        """Return global averages for convenient visualization presets."""
        df = self.features["bands"]
        summary = {
            "bpm": self.features["bpm"],
            "key": self.features["key"],
            "avg_bass": float(df["bass"].mean()),
            "avg_mids": float(df["mids"].mean()),
            "avg_treble": float(df["treble"].mean()),
            "avg_db": float(self.features["loudness"]["rms_db"].mean()),
        }
        return summary

    def export_json(self, path="analysis.json"):
        """Export features and time series to JSON."""
        out = {
            "bpm": self.features.get("bpm"),
            "key": self.features.get("key"),
            "summary": self.summarize(),
            "timeline": {
                "time": self.features["bands"]["time"].tolist(),
                "bass": self.features["bands"]["bass"].tolist(),
                "mids": self.features["bands"]["mids"].tolist(),
                "treble": self.features["bands"]["treble"].tolist(),
                "rms_db": self.features["loudness"]["rms_db"].tolist()
            }
        }
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        print(f"Exported analysis to {path}")
        return out


# Example usage:
if __name__ == "__main__":
    analyzer = AudioAnalyzer("Let_it_be.wav")
    analyzer.load_audio()
    analyzer.analyze_tempo()
    print("Extracted tempo:", analyzer.features.get("tempo"))
    analyzer.analyze_key()
    analyzer.compute_spectral_bands()
    analyzer.compute_loudness()
    print(analyzer.summarize())
    analyzer.export_json("example_analysis.json")
