import librosa
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy import ndimage


class mel_spectrogram:
    def __init__(
        self,
        file_name,
        hop_length=8192,
        n_fft=1024,
        n_mels=128,
        db_min_threshold=-80.0,
        db_max_threshold=0.0,
        do_smoothing=True,
        smooth_sigma=(1.0, 1.5),
        clamp_to_base=True,
        base_plane=-80.0,
    ):
        self.file_name = file_name
        self.hop_length = hop_length
        self.n_fft = n_fft
        self.n_mels = n_mels
        self.db_min_threshold = db_min_threshold
        self.db_max_threshold = db_max_threshold
        self.do_smoothing = do_smoothing
        self.smooth_sigma = smooth_sigma
        self.clamp_to_base = clamp_to_base
        self.base_plane = base_plane

        # Internal storage
        self.sr = None
        self.S_db = None
        self.time_grid = None
        self.mel_grid = None
        self.Z = None

    # ------------------- Processing steps ------------------- #
    def load_audio(self):
        y, self.sr = librosa.load(self.file_name, sr=None)
        return y

    def compute_mel_spectrogram(self, y):
        S = librosa.feature.melspectrogram(
            y=y, sr=self.sr, n_fft=self.n_fft,
            hop_length=self.hop_length, n_mels=self.n_mels,
            fmin=20, fmax=self.sr / 2
        )
        self.S_db = librosa.power_to_db(S, ref=np.max)
        return self.S_db

    def build_grid(self, convert_frames_to_seconds=True):
        n_frames = self.S_db.shape[-1]
        frame_grid = np.arange(n_frames)

        if convert_frames_to_seconds:
            self.time_grid = librosa.frames_to_time(
                frame_grid, sr=self.sr, hop_length=self.hop_length
            )
        else:
            self.time_grid = frame_grid.astype(float)

        self.mel_grid = np.arange(self.S_db.shape[0])
        T, M = np.meshgrid(self.time_grid, self.mel_grid)
        return T, M

    def clean_surface(self, T, M):
        Z = np.copy(self.S_db)

        # Thresholding
        if self.clamp_to_base:
            Z[Z < self.base_plane] = self.base_plane
        else:
            Z[Z <= self.db_min_threshold] = np.nan

        # Gaussian smoothing
        if self.do_smoothing:
            Z = ndimage.gaussian_filter(Z, sigma=self.smooth_sigma)

        self.Z = Z
        return Z

    # ------------------- Output utilities ------------------- #
    def save_to_csv(self, T, M, output_file="mel_spectrogram_points.csv"):
        df = pd.DataFrame({
            "time": T.flatten(),
            "mel_bin": M.flatten(),
            "amplitude": self.Z.flatten()
        })
        df.to_csv(output_file, index=False, header=True)

    def plot_surface(self, T, M, title="Mel Spectrogram 3D Surface"):
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111, projection="3d")
        surf = ax.plot_surface(
            T, M, self.Z, cmap="viridis",
            linewidth=0, antialiased=True
        )
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Mel bin")
        ax.set_zlabel("Amplitude (dB)")
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label="dB")
        plt.title(title)
        plt.tight_layout()
        plt.show()


# ------------------- Usage ------------------- #
def main():
    spectro = mel_spectrogram(
        file_name="Let_it_be.wav",
        smooth_sigma=(1.0, 1.5),
        base_plane=-80.0,
    )

    y = spectro.load_audio()
    spectro.compute_mel_spectrogram(y)
    T, M = spectro.build_grid(convert_frames_to_seconds=True)
    spectro.clean_surface(T, M)

    spectro.save_to_csv(T, M, output_file="mel_spectrogram_points_clean.csv")
    spectro.plot_surface(T, M, title="Cleaned & Smoothed Mel Spectrogram")


if __name__ == "__main__":
    main()
