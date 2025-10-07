from datetime import date
import spectrogram_reader as sr
from sys import argv
from os import system, getcwd, path

jobId = argv[1]
mode = argv[2] if len(argv) > 2 else "none"
print(f"Generating STL for jobId: {jobId}")

def generateCSV():
    print("Generating CSV...")
    # spectro = sr.STFTMelAveraged(
    #         jobId=jobId,
    #         sigma_freq=3,
    #         sigma_time=4
    #     )
    # y = spectro.load_audio()
    # spectro.compute_stft(y)
    # spectro.average_matrix()
    # spectro.apply_gaussian_smoothing()
    # spectro.save_to_csv(jobId)
    # print("CSV generation complete.")

    today = date.today()

    spectro = sr.mel_spectrogram(
        jobId=jobId,
        smooth_sigma=(4.0, 2.0),
        base_plane=-80.0,
    )

    y = spectro.load_audio()
    spectro.compute_mel_spectrogram(y)
    T, M = spectro.build_grid(convert_frames_to_seconds=True)
    spectro.clean_surface(T, M)
    B = spectro.band_labeling(M)

    spectro.save_to_csv(T, M, B, output_file = jobId)
    #spectro.plot_surface(T, M, "Bins = 441")

print("Step 1/2: Generating CSV from audio...")
generateCSV()
print("Step 2/2: Generating STL from CSV...")
if getcwd().startswith("/Users/deadfloppy/Projects/AdditiveWebsite/main-docker"):
    # MacOS
    system(f"/Applications/Blender.app/Contents/MacOS/Blender --background -P ./src/app/api/generate-stl/blenderModelGenerationScript.py -- {jobId} {mode}")
else:
    system(f"blender --background -P ./src/app/api/generate-stl/blenderModelGenerationScript.py -- {jobId} {mode}")
print("Done.")



