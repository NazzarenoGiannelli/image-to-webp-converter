# Image to WebP Converter

A powerful Python script to convert PNG, JPG, and JPEG images to WebP format with advanced features including profile management, parallel processing, and resource optimization.

## Features

- **Multiple Format Support**: Converts PNG, JPG, and JPEG to WebP
- **Parallel Processing**: Fast conversion using multi-threading
- **Profile Management**: Preset and custom conversion profiles
- **Resource Management**:
  - Disk space checking
  - Memory optimization
  - CPU utilization control
- **File Handling**:
  - Recursive directory scanning
  - Original file preservation options
  - Timestamp preservation
  - Duplicate file handling
- **Progress Tracking**: Real-time conversion progress bar
- **Error Handling**: Comprehensive error checking and reporting
- **Configuration**: Save and reuse preferred settings

## Requirements
- Python 3.x
- Required packages (install via requirements.txt):
  - Pillow
  - tqdm
  - psutil

## Installation
```bash
pip install -r requirements.txt
```

## Basic Usage

### Convert a Single File
```bash
python image_to_webp.py input.png
```

### Convert a Directory
```bash
python image_to_webp.py /path/to/directory
```

### Convert Directory Recursively
```bash
python image_to_webp.py /path/to/directory -r
```

## Advanced Options

### Quality and Compression
- `-q`, `--quality`: WebP quality (0-100)
- `--lossless`: Use lossless compression

### Output Control
- `-o`, `--output`: Output file or directory path
- `-r`, `--recursive`: Process subdirectories recursively

### File Handling
- `--keep-originals`: Keep original files (default)
- `--delete-originals`: Delete original files after conversion
- `--no-preserve-timestamps`: Don't preserve original file timestamps

### Profile Management
- `--profile NAME`: Use a specific conversion profile
- `--save-profile NAME`: Save current settings as a new profile
- `--list-profiles`: List all available profiles
- `--set-default-profile NAME`: Set the default profile
- `--use-last`: Use last used settings

## Preset Profiles

### high_quality
- Quality: 95
- Lossless: Yes
- Preserve Timestamps: Yes
- Preserve Originals: Yes

### balanced (default)
- Quality: 80
- Lossless: No
- Preserve Timestamps: Yes
- Preserve Originals: Yes

### web_optimized
- Quality: 75
- Lossless: No
- Preserve Timestamps: No
- Preserve Originals: Yes

### space_saver
- Quality: 60
- Lossless: No
- Preserve Timestamps: No
- Preserve Originals: No

## Examples

### Using Profiles
```bash
# List all profiles
python image_to_webp.py --list-profiles

# Use web-optimized profile
python image_to_webp.py images/ --profile web_optimized

# Create custom profile
python image_to_webp.py images/ -q 85 --lossless --save-profile "my_profile"

# Use last settings
python image_to_webp.py images/ --use-last
```

### Advanced Conversion
```bash
# Recursive conversion with custom output
python image_to_webp.py input_dir/ -r -o output_dir/

# High-quality conversion, delete originals
python image_to_webp.py images/ --profile high_quality --delete-originals

# Custom quality with timestamp preservation
python image_to_webp.py images/ -q 90 --preserve-timestamps
```

## Configuration

The script stores configuration in `~/.png_to_webp/config.json`, including:
- Custom profiles
- Last used settings
- Default profile preference
- Global settings

## Error Handling

The script includes comprehensive error checking for:
- Corrupted images
- Insufficient disk space
- Invalid paths
- Permission issues
- Resource limitations

## Notes

- The script automatically checks for sufficient disk space before conversion
- Memory usage is optimized for large batches of files
- Progress bar shows real-time conversion status
- Detailed logging helps track any issues
- Original directory structure is maintained when using custom output directory
