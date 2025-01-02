import os
from PIL import Image
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import psutil
from PIL import ImageFile
import logging
from typing import Optional, Tuple, Union
from config import Config, PRESET_PROFILES

# Enable loading of truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supported input formats
SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff'}

MIN_FREE_SPACE_MB = 500  # Minimum required free space in MB

class ConversionError(Exception):
    """Custom exception for conversion errors"""
    pass

def check_disk_space(path: str, required_mb: float) -> bool:
    """
    Check if there's enough disk space available.
    
    Args:
        path: Path to check disk space for
        required_mb: Required space in megabytes
    
    Returns:
        bool: True if enough space available, False otherwise
    """
    try:
        free_space = psutil.disk_usage(path).free
        free_space_mb = free_space / (1024 * 1024)  # Convert to MB
        return free_space_mb >= required_mb
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return False

def validate_paths(input_path: str, output_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate input and output paths.
    
    Args:
        input_path: Input file or directory path
        output_path: Optional output path
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        input_path = Path(input_path)
        if not input_path.exists():
            return False, f"Input path does not exist: {input_path}"
        
        if output_path:
            output_path = Path(output_path)
            if output_path.exists() and output_path.is_file() and not output_path.suffix == '.webp':
                return False, f"Output file must have .webp extension: {output_path}"
            
            # Check if output directory is writable
            output_dir = output_path if output_path.is_dir() else output_path.parent
            if output_dir.exists() and not os.access(str(output_dir), os.W_OK):
                return False, f"Output directory is not writable: {output_dir}"
        
        return True, ""
    except Exception as e:
        return False, f"Path validation error: {e}"

def estimate_output_size(input_path: str) -> float:
    """
    Estimate the output file size in MB.
    WebP typically achieves 25-35% smaller file size compared to PNG/JPEG.
    
    Args:
        input_path: Path to input file
    
    Returns:
        float: Estimated size in MB
    """
    try:
        size_bytes = os.path.getsize(input_path)
        estimated_mb = (size_bytes * 0.75) / (1024 * 1024)  # Assuming 25% compression
        return estimated_mb
    except Exception:
        return 1.0  # Return 1MB as a safe default

def generate_unique_filename(output_path: str, prefix: str = "", suffix: str = "") -> str:
    """
    Generate a unique filename if the output path already exists.
    Can add optional prefix and suffix to the filename.
    
    Args:
        output_path: Base output path
        prefix: Optional prefix to add before filename
        suffix: Optional suffix to add before extension
    
    Returns:
        str: Unique filename with optional prefix/suffix
    """
    directory = os.path.dirname(output_path)
    filename = os.path.basename(output_path)
    base, ext = os.path.splitext(filename)
    
    # Apply prefix and suffix
    if prefix or suffix:
        base = f"{prefix}{base}{suffix}"
    
    # First try with just prefix/suffix
    new_path = os.path.join(directory, f"{base}{ext}")
    if not os.path.exists(new_path):
        return new_path
    
    # If exists, add counter
    counter = 1
    while os.path.exists(os.path.join(directory, f"{base}({counter}){ext}")):
        counter += 1
    return os.path.join(directory, f"{base}({counter}){ext}")

def copy_timestamps(source_path: str, target_path: str) -> None:
    """
    Copy timestamp metadata from source file to target file
    """
    try:
        stats = os.stat(source_path)
        os.utime(target_path, (stats.st_atime, stats.st_mtime))
    except Exception as e:
        logger.warning(f"Failed to preserve timestamps: {e}")

def convert_to_webp(input_path: str, output_path: Optional[str] = None, 
                   quality: int = 80, preserve_timestamps: bool = True,
                   lossless: bool = False, prefix: str = "", suffix: str = "") -> Tuple[bool, str, Union[str, Exception]]:
    """
    Convert an image to WebP format while preserving alpha channel.
    
    Args:
        input_path: Path to input image file
        output_path: Path for output WebP file. If None, uses same name as input
        quality: Quality of WebP image (0-100), default 80
        preserve_timestamps: Whether to preserve original file timestamps
        lossless: Whether to use lossless compression
        prefix: Optional prefix to add to output filename
        suffix: Optional suffix to add to output filename before extension
    
    Returns:
        Tuple[bool, str, Union[str, Exception]]: (success, input_path, output_path/error)
    """
    try:
        # Validate input file
        if not os.path.exists(input_path):
            raise ConversionError(f"Input file does not exist: {input_path}")
            
        # Estimate output size and check disk space
        estimated_size = estimate_output_size(input_path)
        if not check_disk_space(os.path.dirname(input_path), estimated_size + MIN_FREE_SPACE_MB):
            raise ConversionError(f"Insufficient disk space. Need at least {estimated_size + MIN_FREE_SPACE_MB}MB free")

        # Open and verify the image
        try:
            with Image.open(input_path) as img:
                # Verify image integrity
                img.verify()
                
                # Reopen image after verify (verify closes the file)
                img = Image.open(input_path)
                
                # If no output path specified, create one
                if output_path is None:
                    output_path = str(Path(input_path).with_suffix('.webp'))
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Handle duplicate files with prefix/suffix
                output_path = generate_unique_filename(output_path, prefix, suffix)
                
                # Convert and save as WebP with memory optimization
                img.save(output_path, 'WEBP', quality=quality, lossless=lossless, optimize=True)
                
                # Preserve timestamps if requested
                if preserve_timestamps:
                    copy_timestamps(input_path, output_path)
                    
                return True, input_path, output_path
                
        except (IOError, SyntaxError) as e:
            raise ConversionError(f"Corrupted or invalid image file: {e}")
            
    except ConversionError as e:
        return False, input_path, e
    except Exception as e:
        return False, input_path, Exception(f"Unexpected error: {e}")

def process_directory(directory_path: str, quality: int = 80, recursive: bool = True,
                     output_dir: Optional[str] = None, preserve_originals: bool = True,
                     copy_timestamps: bool = True, prefix: str = "", suffix: str = "") -> None:
    """
    Convert all supported image files in a directory to WebP format.
    
    Args:
        directory_path: Path to directory containing image files
        quality: Quality of WebP images (0-100)
        recursive: Whether to process subdirectories
        output_dir: Custom output directory path
        preserve_originals: Whether to keep original files
        copy_timestamps: Whether to copy original file timestamps
        prefix: Optional prefix to add to output filenames
        suffix: Optional suffix to add to output filenames before extension
    """
    try:
        directory_path = os.path.abspath(directory_path)
        if not os.path.isdir(directory_path):
            raise ConversionError(f"Not a directory: {directory_path}")
            
        # Create output directory if specified
        if output_dir:
            output_dir = os.path.abspath(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            
        # Collect all image files
        image_files = []
        if recursive:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
                        image_files.append(os.path.join(root, file))
        else:
            image_files = [
                os.path.join(directory_path, f) for f in os.listdir(directory_path)
                if os.path.isfile(os.path.join(directory_path, f)) and
                any(f.lower().endswith(ext) for ext in SUPPORTED_FORMATS)
            ]
            
        if not image_files:
            logger.warning(f"No supported image files found in {directory_path}")
            return
            
        # Process files in parallel
        with ThreadPoolExecutor() as executor:
            futures = []
            for input_path in image_files:
                if output_dir:
                    # Maintain directory structure in output
                    rel_path = os.path.relpath(input_path, directory_path)
                    output_path = os.path.join(output_dir, rel_path)
                    output_path = str(Path(output_path).with_suffix('.webp'))
                else:
                    output_path = None
                    
                future = executor.submit(
                    convert_to_webp,
                    input_path,
                    output_path,
                    quality,
                    copy_timestamps,
                    False,  # lossless
                    prefix,
                    suffix
                )
                futures.append((input_path, future))
            
            # Process results with progress bar
            successful = 0
            failed = 0
            with tqdm(total=len(futures), desc="Converting images", unit="file") as pbar:
                for input_path, future in futures:
                    try:
                        success, _, result = future.result()
                        if success:
                            successful += 1
                            if not preserve_originals:
                                try:
                                    os.remove(input_path)
                                except Exception as e:
                                    logger.error(f"Failed to delete original file {input_path}: {e}")
                        else:
                            failed += 1
                            logger.error(f"Failed to convert {input_path}: {result}")
                    except Exception as e:
                        failed += 1
                        logger.error(f"Error processing {input_path}: {e}")
                    finally:
                        pbar.update(1)
            
            logger.info(f"Conversion complete. Successful: {successful}, Failed: {failed}")
            
    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {e}")

def main():
    # Initialize configuration
    config = Config()
    
    # Create argument parser
    parser = argparse.ArgumentParser(description='Convert images to WebP format')
    parser.add_argument('input', help='Input image file or directory')
    parser.add_argument('-q', '--quality', type=int,
                        help='WebP quality (0-100)')
    parser.add_argument('-o', '--output', help='Output WebP file or directory')
    parser.add_argument('-r', '--recursive', action='store_true', 
                        help='Recursively process subdirectories')
    parser.add_argument('--keep-originals', action='store_true',
                        help='Keep original files')
    parser.add_argument('--delete-originals', action='store_true',
                        help='Delete original files after conversion')
    parser.add_argument('--no-preserve-timestamps', action='store_true',
                        help='Do not preserve original file timestamps')
    parser.add_argument('--profile', help='Use specific conversion profile')
    parser.add_argument('--save-profile', help='Save current settings as a new profile')
    parser.add_argument('--list-profiles', action='store_true',
                        help='List all available profiles')
    parser.add_argument('--set-default-profile',
                        help='Set the default profile')
    parser.add_argument('--lossless', action='store_true',
                        help='Use lossless compression')
    parser.add_argument('--use-last', action='store_true',
                        help='Use last used settings')
    parser.add_argument('--prefix', help='Add prefix to output filename')
    parser.add_argument('--suffix', help='Add suffix to output filename before extension')
    
    args = parser.parse_args()
    
    try:
        # Handle profile listing
        if args.list_profiles:
            profiles = config.list_all_profiles()
            print("\nAvailable profiles:")
            for name, settings in profiles.items():
                print(f"\n{name}:")
                for key, value in settings.items():
                    print(f"  {key}: {value}")
            return 0

        # Handle setting default profile
        if args.set_default_profile:
            if config.set_default_profile(args.set_default_profile):
                print(f"Set default profile to: {args.set_default_profile}")
                return 0
            else:
                print(f"Error: Profile '{args.set_default_profile}' not found")
                return 1

        # Load settings from profile or last used settings
        if args.use_last:
            settings = config.get_last_used_settings()
            if not settings:
                print("No last used settings found, using default profile")
                settings = config.get_profile()
        elif args.profile:
            settings = config.get_profile(args.profile)
        else:
            settings = config.get_profile()

        # Override profile settings with command line arguments
        if args.quality is not None:
            settings['quality'] = args.quality
        if args.lossless is not None:
            settings['lossless'] = args.lossless
        if args.keep_originals:
            settings['preserve_originals'] = True
        if args.delete_originals:
            settings['preserve_originals'] = False
        if args.no_preserve_timestamps:
            settings['preserve_timestamps'] = False

        # Save current settings for future use
        current_settings = {
            'quality': settings['quality'],
            'lossless': settings['lossless'],
            'preserve_timestamps': settings['preserve_timestamps'],
            'preserve_originals': settings['preserve_originals']
        }
        config.save_last_used_settings(current_settings)

        # Save as new profile if requested
        if args.save_profile:
            config.save_custom_profile(args.save_profile, current_settings)
            print(f"Saved current settings as profile: {args.save_profile}")

        # Handle conflicting arguments
        if args.keep_originals and args.delete_originals:
            raise ValueError("Cannot specify both --keep-originals and --delete-originals")
        
        # Validate paths
        is_valid, error_msg = validate_paths(args.input, args.output)
        if not is_valid:
            raise ValueError(error_msg)
        
        if os.path.isfile(args.input):
            success, _, result = convert_to_webp(
                args.input, 
                args.output, 
                settings['quality'],
                settings['preserve_timestamps'],
                settings['lossless'],
                args.prefix,
                args.suffix
            )
            if success:
                logger.info(f"Successfully converted {args.input} to {result}")
                if not settings['preserve_originals']:
                    try:
                        os.remove(args.input)
                        logger.info(f"Deleted original: {args.input}")
                    except Exception as e:
                        logger.error(f"Failed to delete original {args.input}: {e}")
            else:
                logger.error(f"Error: {result}")
        elif os.path.isdir(args.input):
            process_directory(
                args.input,
                settings['quality'],
                args.recursive,
                args.output,
                settings['preserve_originals'],
                settings['preserve_timestamps'],
                args.prefix,
                args.suffix
            )
        else:
            raise ValueError(f"Error: {args.input} is not a valid file or directory")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
