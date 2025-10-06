import librosa
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt
from sys import argv


class STFTMelAveraged:
    def __init__(self, file_name, n_fft=2048, hop_length=4096,
                 sigma_freq=1, sigma_time=1):
        self.file_name = file_name
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.sigma_freq = sigma_freq
        self.sigma_time = sigma_time

        # Internals
        self.sr = None
        self.times = None
        self.freqs = None
        self.S_db = None
        self.S_reduced = None
        self.freqs_reduced = None
        self.times_reduced = None

    def load_audio(self):
        y, self.sr = librosa.load(self.file_name, sr=None)
        return y

    def compute_stft(self, y):
        D = librosa.stft(y, n_fft=self.n_fft, hop_length=self.hop_length)
        S = np.abs(D) ** 2
        S_db = librosa.power_to_db(S, ref=np.max)
        self.S_db = S_db
        self.freqs = librosa.fft_frequencies(sr=self.sr, n_fft=self.n_fft)
        self.times = librosa.frames_to_time(
            np.arange(S.shape[1]), sr=self.sr, hop_length=self.hop_length
        )
        return S_db

    def average_matrix(self, max_time_bins=300):
        freq_bins, time_bins = self.S_db.shape

        if time_bins > max_time_bins:
            # Downsample along time axis
            time_edges = np.linspace(0, time_bins, max_time_bins + 1, dtype=int)
            reduced = np.zeros((freq_bins, max_time_bins))

            for j in range(max_time_bins):
                time_slice = slice(time_edges[j], time_edges[j + 1])
                reduced[:, j] = np.mean(self.S_db[:, time_slice], axis=1)

            self.S_reduced = reduced
            self.times_reduced = np.linspace(
                self.times.min(), self.times.max(), max_time_bins
            )
        else:
            # Keep original resolution
            self.S_reduced = self.S_db
            self.times_reduced = self.times

        # Frequencies always stay the same
        self.freqs_reduced = self.freqs
        return self.S_reduced

    def apply_gaussian_smoothing(self):
        if self.S_reduced is not None:
            # Apply 2D Gaussian smoothing with different sigmas
            self.S_reduced = gaussian_filter(
                self.S_reduced,
                sigma=(self.sigma_freq, self.sigma_time)
            )
        return self.S_reduced

    def add_mel_column(self):
        mel = 2595 * np.log10(1 + self.freqs_reduced / 700)
        return mel

    def save_to_csv(self, output_file=f"jobId.csv"):
        rows = []
        mel = self.add_mel_column()
        for i, f in enumerate(self.freqs_reduced):
            for j, t in enumerate(self.times_reduced):
                amp = self.S_reduced[i, j]
                rows.append((t, mel[i], amp, f))
        df = pd.DataFrame(rows, columns=["time", "mel", "amplitude", "frequency"])
        df.to_csv(output_file, index=False)
        print(f"CSV saved to {output_file}")

    def plot_surface(self):
        """Original 3D plot with frequency axis."""
        T, F = np.meshgrid(self.times_reduced, self.freqs_reduced)
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111, projection="3d")
        surf = ax.plot_surface(T, F, self.S_reduced, cmap="viridis")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        ax.set_zlabel("Amplitude (dB)")
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
        plt.show()

    def plot_surface_mel(self):
        """New 3D plot with mel bins instead of frequency."""
        mel = self.add_mel_column()
        T, M = np.meshgrid(self.times_reduced, mel)
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111, projection="3d")
        surf = ax.plot_surface(T, M, self.S_reduced, cmap="plasma")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Mel scale")
        ax.set_zlabel("Amplitude (dB)")
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
        plt.show()


def main(jobId):
    spectro = STFTMelAveraged(
        file_name=jobId,
        sigma_freq=3,
        sigma_time=4
    )
    y = spectro.load_audio()
    spectro.compute_stft(y)
    spectro.average_matrix()
    spectro.apply_gaussian_smoothing()
    spectro.save_to_csv(f"{jobId}.csv")
    # spectro.plot_surface_mel()  # <-- use mel-bin 3D plot
    # spectro.plot_surface()


if __name__ == "__main__":
    main()
