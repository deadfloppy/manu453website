import spectrogram_reader as sr
from sys import argv
from os import system

jobId = argv[1]
print(f"Generating STL for jobId: {jobId}")

def generateCSV():
    print("Generating CSV...")
    spectro = sr.STFTMelAveraged(
            file_name=jobId,
            sigma_freq=3,
            sigma_time=4
        )
    y = spectro.load_audio()
    spectro.compute_stft(y)
    spectro.average_matrix()
    spectro.apply_gaussian_smoothing()
    path = f"/Users/deadfloppy/Projects/AdditiveWebsite/with-docker/tmp/{jobId}/{jobId}.csv"
    spectro.save_to_csv(path)
    print("CSV generation complete.")

print("Step 1/2: Generating CSV from audio...")
generateCSV()
print("Step 2/2: Generating STL from CSV...")
system(f"/Applications/Blender.app/Contents/MacOS/Blender --background -P ./src/app/api/generate-stl/blenderModelGenerationScript.py -- {jobId}")
print("Done.")



