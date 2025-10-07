import spectrogram_reader as sr
from sys import argv
from os import system, getcwd, path

jobId = argv[1]
print(f"Generating STL for jobId: {jobId}")

def generateCSV():
    print("Generating CSV...")
    spectro = sr.STFTMelAveraged(
            jobId=jobId,
            sigma_freq=3,
            sigma_time=4
        )
    y = spectro.load_audio()
    spectro.compute_stft(y)
    spectro.average_matrix()
    spectro.apply_gaussian_smoothing()
    spectro.save_to_csv(jobId)
    print("CSV generation complete.")

print("Step 1/2: Generating CSV from audio...")
generateCSV()
print("Step 2/2: Generating STL from CSV...")
if getcwd().startswith("/Users/deadfloppy/Projects/AdditiveWebsite/with-docker"):
    # MacOS
    system(f"/Applications/Blender.app/Contents/MacOS/Blender --background -P ./src/app/api/generate-stl/blenderModelGenerationScript.py -- {jobId}")
else:
    system(f"blender --background -P ./src/app/api/generate-stl/blenderModelGenerationScript.py -- {jobId}")
print("Done.")



