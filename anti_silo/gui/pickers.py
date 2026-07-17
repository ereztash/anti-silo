from __future__ import annotations

from pathlib import Path


def _default_desktop_dir() -> Path:
    home = Path.home()
    candidates = [
        home / "Desktop",
        home / "OneDrive" / "Desktop",
        home / "שולחן העבודה",
        home / "OneDrive" / "שולחן העבודה",
    ]
    return next((path for path in candidates if path.is_dir()), home)


def _choose_folder() -> str:
    """Use the operating system folder picker when a desktop session is available."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(initialdir=str(_default_desktop_dir()), title="Choose a folder for Anti-Silo")
        root.destroy()
        return selected
    except Exception as exc:
        raise ValueError("Could not open the system folder picker.") from exc


def _choose_file() -> str:
    """Use the operating system file picker for an independent source."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askopenfilename(initialdir=str(_default_desktop_dir()), title="Choose an independent source")
        root.destroy()
        return selected
    except Exception as exc:
        raise ValueError("Could not open the system file picker.") from exc
