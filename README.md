# PNG to WebP Converter

A Python script to convert PNG images to WebP format while preserving alpha channels (transparency).

## Requirements
- Python 3.x
- Pillow library

## Installation
```bash
pip install -r requirements.txt
```

## Usage

### Convert a single PNG file
```bash
python png_to_webp.py input.png
```

### Convert a single PNG file with custom quality
```bash
python png_to_webp.py input.png -q 90
```

### Convert a single PNG file with custom output path
```bash
python png_to_webp.py input.png -o output.webp
```

### Convert all PNG files in a directory
```bash
python png_to_webp.py /path/to/directory
```

## Options
- `-q`, `--quality`: WebP quality (0-100), default is 80
- `-o`, `--output`: Output WebP file path (only for single file conversion)
