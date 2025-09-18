import librosa
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy import interpolate, ndimage

# Parameters
file_name = "humpback_whale_sounds.wav"
hop_length = 8192
n_fft = 1024
n_mels = 64
db_min_threshold = -80.0  # -80 dB is min
db_max_threshold = 0.0  # 0 dB is max

# Cleanup parameters
do_interpolation = True       # Fill missing values
do_smoothing = True           # Apply Gaussian smoothing
smooth_sigma = (1.0, 1.5)     # (mel, time) smoothing strength
clamp_to_base = True          # Clamp quiet values to base plane
base_plane = db_min_threshold  # Where to clamp quiet amplitudes


def main(plot_surface=True, convert_frames_to_seconds=True):
    # Load audio
    y, sr = librosa.load(file_name, sr=None)

    # Compute Mel spectrogram
    S = librosa.feature.melspectrogram(
        y=y, sr=sr, n_fft=n_fft, hop_length=hop_length,
        n_mels=n_mels, fmin=20, fmax=sr / 2
    )

    # Convert power to decibels
    S_db = librosa.power_to_db(S, ref=np.max)

    # Mask amplitudes within thresholds
    if db_max_threshold is None:
        mask = S_db > db_min_threshold
    else:
        mask = (S_db > db_min_threshold) & (S_db < db_max_threshold)

    mel_idx, time_idx = np.where(mask)
    amps = S_db[mel_idx, time_idx]

    # Optionally convert frame indices to seconds
    if convert_frames_to_seconds:
        times = librosa.frames_to_time(time_idx, sr=sr, hop_length=hop_length)
    else:
        times = time_idx.astype(float)

    # Save raw point cloud to CSV
    df_raw = pd.DataFrame(
        {"time": times, "mel_bin": mel_idx, "amplitude": amps})
    df_raw.to_csv("mel_spectrogram_points_raw.csv", index=False, header=True)

    # Build full grid for cleanup
    n_frames = S_db.shape[-1]
    frame_grid = np.arange(n_frames)
    if convert_frames_to_seconds:
        time_grid = librosa.frames_to_time(
            frame_grid, sr=sr, hop_length=hop_length)
    else:
        time_grid = frame_grid.astype(float)
    mel_grid = np.arange(S_db.shape[0])
    T, M = np.meshgrid(time_grid, mel_grid)

    # Copy full spectrogram
    Z = np.copy(S_db)

    # Clamp values to base plane instead of dropping them
    if clamp_to_base:
        Z[Z < base_plane] = base_plane
    else:
        Z[Z <= db_min_threshold] = np.nan  # keep NaNs if not clamping

    # --- Gaussian smoothing across both axes ---
    if do_smoothing:
        Z = ndimage.gaussian_filter(Z, sigma=smooth_sigma)

    # Save cleaned surface to CSV
    df_clean = pd.DataFrame({
        "time": T.flatten(),
        "mel_bin": M.flatten(),
        "amplitude": Z.flatten()
    })
    df_clean.to_csv("mel_spectrogram_points_clean.csv",
                    index=False, header=True)

    # Plot 3D surface
    if plot_surface:
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111, projection="3d")
        surf = ax.plot_surface(T, M, Z, cmap="viridis",
                               linewidth=0, antialiased=True)
        ax.set_xlabel("Time (s)" if convert_frames_to_seconds else "Frame")
        ax.set_ylabel("Mel bin")
        ax.set_zlabel("Amplitude (dB)")
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label="dB")
        plt.title("Cleaned Mel Spectrogram Surface (Gaussian Smoothed)")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main(plot_surface=True, convert_frames_to_seconds=True)
