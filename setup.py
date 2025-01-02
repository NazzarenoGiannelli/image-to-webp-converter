import sys
import os
from cx_Freeze import setup, Executable
import tkinter
import tkinterdnd2

# Get tkinterdnd2 path
tkdnd_path = os.path.dirname(tkinterdnd2.__file__)

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": [
        "tkinter",
        "tkinterdnd2",
        "PIL",
        "pystray",
        "psutil",
    ],
    "includes": [
        "tkinter",
        "tkinterdnd2",
        "PIL._tkinter_finder",
        "PIL._imaging",
        "PIL._webp",
        "PIL.Image",
        "PIL.ImageOps",
    ],
    "excludes": [
        "unittest", "test", "tests", "testing",
        "matplotlib", "numpy", "pandas", "scipy",
        "notebook", "jupyter", "IPython", "ipykernel",
        "tornado", "zmq", "jedi", "setuptools",
        "pkg_resources", "distutils", "cx_Freeze",
    ],
    "include_files": [
        ("config.py", "config.py"),
        ("image_to_webp.py", "image_to_webp.py"),
        ("assets", "assets"),
        # Include tkinterdnd2 files
        (os.path.join(tkdnd_path, "tkdnd"), "tkdnd"),
        (tkdnd_path, "lib/tkinterdnd2"),
    ],
    # Don't zip any packages to ensure all DLLs are accessible
    "zip_include_packages": [],
    "zip_exclude_packages": "*",
    "include_msvcr": True,
    "optimize": 2,
}

# Add TCL/TK files
tcl_tk_files = [
    ("tcl86t.dll", ""),
    ("tk86t.dll", ""),
    ("tcl", "tcl"),
    ("tk", "tk"),
]

python_dir = os.path.dirname(sys.executable)
for src, dst in tcl_tk_files:
    src_path = os.path.join(python_dir, src)
    if os.path.exists(src_path):
        build_exe_options["include_files"].append((src_path, dst))

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
            target_name="image_to_webp_converter_win64.exe",
            shortcut_name="Image to WebP Converter",
            shortcut_dir="DesktopFolder"
        )
    ]
)
