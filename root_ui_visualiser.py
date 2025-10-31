#!/usr/bin/env python3
# visualizer_ui_ctk.py
import os
import sys
import subprocess
import importlib.util
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog, messagebox  # works fine alongside CTk

# --- Settings ---
SPECTROGRAM_CANDIDATES = [
    "spectrogram_visualiser_2point5D.py",  # your uploaded name
    "spectrogram_visualizer2point5d.py",   # tolerated alt spelling
]
WAVEFORMS_FILENAME = "audio_visual_staticwaves.py"
ALLOWED_EXTS = {".wav", ".mp3"}

ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR

# --- Helpers ---
def script_exists(name: str) -> bool:
    return (SCRIPTS_DIR / name).is_file()

def pick_existing(candidates):
    for n in candidates:
        if script_exists(n):
            return n
    return None

def try_import_and_run(script_path: Path, audio_path: str) -> bool:
    """
    Import the visualizer and call a likely entrypoint with audio_path.
    Return True if we started it in-process, False to fall back to subprocess.
    """
    try:
        spec = importlib.util.spec_from_file_location("viz_mod", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore

        for fn in ("main", "run", "run_visualizer", "launch"):
            if hasattr(mod, fn) and callable(getattr(mod, fn)):
                getattr(mod, fn)(audio_path)
                return True
        return False
    except Exception as e:
        print(f"[import fallback] {e}")
        return False

def launch_script(script_filename: str, audio_path: str, force_subprocess: bool = False):
    spath = SCRIPTS_DIR / script_filename

    # 1) Prefer in-process import unless we explicitly force subprocess
    if not force_subprocess and try_import_and_run(spath, audio_path):
        return

    # 2) Fallback: spawn a subprocess, provide the path three ways.
    env = os.environ.copy()
    env["AUDIO_PATH"] = audio_path
    cmd = [sys.executable, str(spath), audio_path, "--audio", audio_path]
    try:
        subprocess.Popen(cmd, env=env, cwd=str(SCRIPTS_DIR))
    except Exception as e:
        messagebox.showerror("Launch failed", f"Could not start {script_filename}\n\n{e}")

def validate_audio(path: str) -> bool:
    return bool(path) and Path(path).suffix.lower() in ALLOWED_EXTS and Path(path).is_file()

# --- UI ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Global appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

        self.title("Audio Visualizer Launcher")
        self.geometry("640x280")
        self.minsize(560, 260)

        # State
        self.audio_path = ctk.StringVar(value="")
        self.preset = ctk.StringVar(value="")

        # Layout
        self.grid_columnconfigure(0, weight=1)

        # Title / subtitle
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(header, text="Audio Visualizer Launcher", font=("Inter", 22, "bold"))
        subtitle = ctk.CTkLabel(header, text="Pick an audio file and a preset to launch.",
                                font=("Inter", 13))
        title.grid(row=0, column=0, sticky="w")
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # File picker card
        file_card = ctk.CTkFrame(self)
        file_card.grid(row=1, column=0, sticky="ew", padx=20, pady=8)
        file_card.grid_columnconfigure(1, weight=1)

        lbl_file = ctk.CTkLabel(file_card, text="Audio file")
        self.ent_file = ctk.CTkEntry(file_card, textvariable=self.audio_path, placeholder_text="No file selected")
        btn_browse = ctk.CTkButton(file_card, text="Browse…", command=self.choose_file)

        lbl_file.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="w")
        self.ent_file.grid(row=0, column=1, padx=(0, 8), pady=12, sticky="ew")
        btn_browse.grid(row=0, column=2, padx=(0, 12), pady=12)

        # Preset card
        preset_card = ctk.CTkFrame(self)
        preset_card.grid(row=2, column=0, sticky="ew", padx=20, pady=8)
        preset_card.grid_columnconfigure(1, weight=1)

        lbl_preset = ctk.CTkLabel(preset_card, text="Preset")
        self.opt_preset = ctk.CTkOptionMenu(
            preset_card,
            variable=self.preset,
            values=["Spectrogram 2.5D", "Waveforms"],
            command=lambda _: self.refresh_continue_state()
        )

        lbl_preset.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="w")
        self.opt_preset.grid(row=0, column=1, padx=(0, 12), pady=12, sticky="ew")

        # Footer actions
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(8, 16))
        footer.grid_columnconfigure(0, weight=1)

        self.btn_continue = ctk.CTkButton(footer, text="Continue →", command=self.on_continue, state="disabled")
        self.btn_continue.grid(row=0, column=1, sticky="e")

        # Reactive state
        self.audio_path.trace_add("write", lambda *_: self.refresh_continue_state())

        # Optional: set default last-opened directory hint
        self._last_dir = str(Path.home())

        #Center and raise window
        self.after(50, self._center_and_raise)

    def _center_and_raise(self):
        # ensure sizes are measured
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        # fall back to requested if width=1 (first draw on some systems)
        if w <= 1 or h <= 1:
            w = 640; h = 280
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 3)   # a bit higher than exact center looks nicer
        self.geometry(f"{w}x{h}+{x}+{y}")

        # bring to front without staying always-on-top
        self.lift()
        try:
            self.attributes("-topmost", True)
            # turn it off shortly after so it behaves normally
            self.after(250, lambda: self.attributes("-topmost", False))
        except Exception:
            pass
        self.focus_force()

    # --- Callbacks ---
    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Choose audio file",
            parent=self,
            initialdir=self._last_dir,
            filetypes=[("Audio files", "*.wav *.mp3"), ("All files", "*.*")]
        )
        if not path:
            return
        if not validate_audio(path):
            messagebox.showwarning("Unsupported file", "Please choose a .wav or .mp3 file.")
            return
        self.audio_path.set(path)
        self._last_dir = str(Path(path).parent)

    def refresh_continue_state(self):
        ok = validate_audio(self.audio_path.get()) and bool(self.preset.get())
        self.btn_continue.configure(state=("normal" if ok else "disabled"))

    def on_continue(self):
        audio_path = self.audio_path.get().strip()
        preset = self.preset.get().strip()

        if not validate_audio(audio_path):
            messagebox.showwarning("Missing audio", "Please pick a valid .wav or .mp3 file.")
            return
        if not preset:
            messagebox.showwarning("Pick a preset", "Please choose a visualizer preset.")
            return

        if preset == "Spectrogram 2.5D":
            spectro = pick_existing(SPECTROGRAM_CANDIDATES)
            if not spectro:
                messagebox.showerror(
                    "File not found",
                    "Couldn't find your spectrogram script.\nExpected one of:\n- " +
                    "\n- ".join(SPECTROGRAM_CANDIDATES)
                )
                return
            launch_script(spectro, audio_path)

        elif preset == "Waveforms":
            if not script_exists(WAVEFORMS_FILENAME):
                messagebox.showerror("File not found", f"Couldn't find {WAVEFORMS_FILENAME} next to this launcher.")
                return
            # 👇 Force a separate process to avoid two Tk roots colliding
            launch_script(WAVEFORMS_FILENAME, audio_path, force_subprocess=True)

        # Close the launcher once a visualizer is started
        self.destroy()

# --- Main ---
if __name__ == "__main__":
    App().mainloop()
