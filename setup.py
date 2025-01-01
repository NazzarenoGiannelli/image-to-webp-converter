import sys
import os
from cx_Freeze import setup, Executable

# Get tkinterdnd2 path
import tkinterdnd2
tkdnd_path = os.path.dirname(tkinterdnd2.__file__)

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": [
        "os", 
        "tkinter", 
        "tkinterdnd2", 
        "PIL", 
        "pystray",
        "psutil",
        "sys",
        "json",
        "threading"
    ],
    "includes": [
        "tkinter",
        "tkinterdnd2",
        "PIL._tkinter_finder"
    ],
    "include_files": [
        ("config.py", "config.py"),
        ("image_to_webp.py", "image_to_webp.py"),
        ("assets", "assets"),  # This will copy the entire assets folder
        (tkdnd_path, "lib/tkinterdnd2"),
    ],
    "excludes": ["tkinter.test", "unittest"],
    "include_msvcr": True,  # Include Visual C++ runtime
}

# Base for GUI applications
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="Image to WebP Converter",
    version="1.0",
    description="Convert images to WebP format",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "gui.py",
            base=base,
            icon="assets/logo-square.ico",
            target_name="ImageToWebPConverter.exe",
            shortcut_name="Image to WebP Converter",
            shortcut_dir="DesktopFolder"
        )
    ]
)
