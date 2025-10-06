import spectrogram_reader as sr
import os
import platform
from sys import argv
from os import system

jobId = argv[1]
print(f"Generating STL for jobId: {jobId}")

def generateCSV():
    print("Generating CSV...")

    tmp_dir = os.path.join(os.getcwd(), "tmp", jobId)
    audio_file = os.path.join(tmp_dir, f"{jobId}.wav")

    spectro = sr.STFTMelAveraged(
            file_name=audio_file,
            sigma_freq=3,
            sigma_time=4
        )
    y = spectro.load_audio()
    spectro.compute_stft(y)
    spectro.average_matrix()
    spectro.apply_gaussian_smoothing()
    csv_path = os.path.join(tmp_dir, f"{jobId}.csv")
    spectro.save_to_csv(csv_path)
    print("CSV generation complete.")

print("Step 1/2: Generating CSV from audio...")
generateCSV()
print("Step 2/2: Generating STL from CSV...")

#MultiOS support
if platform.system() == "Darwin":  # Mac
    blender_path = "/Applications/Blender.app/Contents/MacOS/Blender"
elif platform.system() == "Windows":
    blender_path = r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe"
else:  # Linux
    blender_path = "blender"

script_path = os.path.join("src", "app", "api", "generate-stl", "blenderModelGenerationScript.py")
os.system(f'"{blender_path}" --background -P {script_path} -- {jobId}')

print("Done.")



