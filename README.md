# Image to WebP Converter

![Image to WebP Converter Screenshot](assets/screenshot.jpeg)

A powerful Python application to convert PNG, JPG, and JPEG images to WebP format, featuring both a modern GUI and command-line interface. Includes advanced features like profile management, parallel processing, and resource optimization.

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

## GUI Features
- **Modern Dark Theme**:
  - Sleek dark background
  - Clean, minimal design
  - Responsive layout
- **User-Friendly Interface**:
  - Drag-and-drop support
  - System tray integration
  - Live quality adjustment
  - Collapsible settings panel

## Requirements
- Python 3.x
- Required packages (install via requirements.txt):
  ```
  # Core dependencies
  Pillow
  psutil
  tqdm  # For CLI progress bars
  
  # GUI dependencies
  tkinterdnd2  # For drag-and-drop
  pystray  # For system tray
  ```

## Installation
```bash
pip install -r requirements.txt
```

## Using the GUI

1. **Launch the Application**:
   ```bash
   python gui.py
   ```

2. **Convert Images**:
   - Drag and drop files/folders into the drop zone
   - Or click to select files using the file browser
   - Watch real-time conversion progress

3. **Customize Settings**:
   - Quality (0-100 slider)
   - Lossless compression toggle
   - Original file preservation
   - Timestamp preservation
   - Recursive directory processing

4. **Profile Management**:
   - Select from preset profiles
   - Save custom profiles
   - Set default profile
   - Quick-load last used settings

5. **System Tray Features**:
   - Minimize to tray
   - Quick access menu
   - Background operation

## Command Line Usage

### Basic Usage

```bash
# Convert a single file
python image_to_webp.py input.png

# Convert a directory
python image_to_webp.py /path/to/directory

# Convert directory recursively
python image_to_webp.py /path/to/directory -r
```

### Advanced Options

#### Quality and Compression
- `-q`, `--quality`: WebP quality (0-100)
- `--lossless`: Use lossless compression

#### Output Control
- `-o`, `--output`: Output file or directory path
- `-r`, `--recursive`: Process subdirectories recursively

#### File Handling
- `--keep-originals`: Keep original files (default)
- `--delete-originals`: Delete original files after conversion
- `--no-preserve-timestamps`: Don't preserve original file timestamps

#### Profile Management
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

## Windows Executable

A standalone Windows executable is available, which doesn't require Python installation.

### Building the Executable

1. **Install Build Dependencies**:
   ```bash
   pip install cx_Freeze
   ```

2. **Build the Executable**:
   ```bash
   python setup.py build
   ```
   This will create a `build` directory containing the executable and all required dependencies.

3. **Executable Location**:
   After building, find the executable at:
   ```
   build/exe.win-amd64-3.10/ImageToWebPConverter.exe
   ```

### Features of the Windows Build
- **Standalone Operation**: No Python installation required
- **System Integration**:
  - Desktop shortcut creation
  - System tray support
  - File association capabilities
- **Resource Management**:
  - Bundled with all necessary dependencies
  - Optimized for Windows environment
  - Visual C++ runtime included

### Distribution
To distribute the application:
1. Copy the entire contents of the `build/exe.win-amd64-3.10` directory
2. Share the folder with end users
3. Users can run the application directly by executing `ImageToWebPConverter.exe`

### Notes
- The executable includes all necessary DLLs and dependencies
- Windows Defender or other antivirus software might need to verify the executable
- Requires Windows 7 or later

## Configuration

The application stores configuration in `~/.png_to_webp/config.json`, including:
- Custom profiles
- Last used settings
- Default profile preference
- Global settings

## Error Handling

The application includes comprehensive error checking for:
- Corrupted images
- Insufficient disk space
- Invalid paths
- Permission issues
- Resource limitations

## Notes

- Automatically checks for sufficient disk space before conversion
- Memory usage is optimized for large batches of files
- Progress tracking in both GUI and CLI
- Detailed logging helps track any issues
- Original directory structure is maintained when using custom output directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
