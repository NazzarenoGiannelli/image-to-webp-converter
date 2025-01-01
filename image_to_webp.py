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

SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg'}
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

def generate_unique_filename(output_path: str) -> str:
    """
    Generate a unique filename if the output path already exists.
    Adds a number suffix before the extension (e.g., image(1).webp)
    """
    if not os.path.exists(output_path):
        return output_path
    
    base, ext = os.path.splitext(output_path)
    counter = 1
    while os.path.exists(f"{base}({counter}){ext}"):
        counter += 1
    return f"{base}({counter}){ext}"

def preserve_timestamps(source_path: str, target_path: str) -> None:
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
                   lossless: bool = False) -> Tuple[bool, str, Union[str, Exception]]:
    """
    Convert an image to WebP format while preserving alpha channel.
    
    Args:
        input_path: Path to input image file
        output_path: Path for output WebP file. If None, uses same name as input
        quality: Quality of WebP image (0-100), default 80
        preserve_timestamps: Whether to preserve original file timestamps
        lossless: Whether to use lossless compression
    
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
                
                # Handle duplicate files
                output_path = generate_unique_filename(output_path)
                
                # Convert and save as WebP with memory optimization
                img.save(output_path, 'WEBP', quality=quality, lossless=lossless, optimize=True)
                
                # Preserve timestamps if requested
                if preserve_timestamps:
                    preserve_timestamps(input_path, output_path)
                    
                return True, input_path, output_path
                
        except (IOError, SyntaxError) as e:
            raise ConversionError(f"Corrupted or invalid image file: {e}")
            
    except ConversionError as e:
        return False, input_path, e
    except Exception as e:
        return False, input_path, Exception(f"Unexpected error: {e}")

def process_directory(directory_path: str, quality: int = 80, recursive: bool = True,
                     output_dir: Optional[str] = None, preserve_originals: bool = True,
                     preserve_timestamps: bool = True) -> None:
    """
    Convert all supported image files in a directory to WebP format.
    
    Args:
        directory_path: Path to directory containing image files
        quality: Quality of WebP images (0-100)
        recursive: Whether to process subdirectories
        output_dir: Custom output directory path
        preserve_originals: Whether to keep original files
        preserve_timestamps: Whether to preserve original file timestamps
    """
    try:
        directory = Path(directory_path)
        
        # Validate input directory
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")
        
        # Get all files with supported extensions
        if recursive:
            files = [f for f in directory.rglob("*") if f.suffix.lower() in SUPPORTED_FORMATS]
        else:
            files = [f for f in directory.glob("*") if f.suffix.lower() in SUPPORTED_FORMATS]
        
        if not files:
            logger.warning(f"No supported image files found in {directory_path}")
            return

        # Calculate total input size
        total_size_mb = sum(estimate_output_size(str(f)) for f in files)
        
        # Check disk space
        if output_dir:
            if not check_disk_space(output_dir, total_size_mb + MIN_FREE_SPACE_MB):
                raise ConversionError(
                    f"Insufficient disk space in output directory. "
                    f"Need at least {total_size_mb + MIN_FREE_SPACE_MB}MB free"
                )
        elif not check_disk_space(directory_path, total_size_mb + MIN_FREE_SPACE_MB):
            raise ConversionError(
                f"Insufficient disk space. Need at least {total_size_mb + MIN_FREE_SPACE_MB}MB free"
            )

        # Create progress bar
        pbar = tqdm(total=len(files), desc="Converting images", unit="file")
        
        # Process files in parallel with memory-optimized batch size
        max_workers = min(32, os.cpu_count() + 4)  # Limit max workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all conversion tasks
            future_to_file = {}
            for f in files:
                if output_dir:
                    # Maintain relative directory structure in output directory
                    rel_path = f.relative_to(directory)
                    new_path = Path(output_dir) / rel_path
                    output_path = str(new_path.with_suffix('.webp'))
                else:
                    output_path = None
                    
                future = executor.submit(
                    convert_to_webp, 
                    str(f), 
                    output_path,
                    quality,
                    preserve_timestamps
                )
                future_to_file[future] = f
            
            # Process results as they complete
            for future in as_completed(future_to_file):
                success, input_path, result = future.result()
                if success:
                    logger.info(f"✓ Converted: {input_path} -> {result}")
                    # Delete original if not preserving
                    if not preserve_originals:
                        try:
                            os.remove(input_path)
                            logger.info(f"  Deleted original: {input_path}")
                        except Exception as e:
                            logger.error(f"  Failed to delete original {input_path}: {e}")
                else:
                    logger.error(f"✗ Failed to convert {input_path}: {result}")
                pbar.update(1)
        
        pbar.close()
        
    except Exception as e:
        logger.error(f"Error processing directory: {e}")
        raise

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
                settings['lossless']
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
                settings['preserve_timestamps']
            )
        else:
            raise ValueError(f"Error: {args.input} is not a valid file or directory")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
