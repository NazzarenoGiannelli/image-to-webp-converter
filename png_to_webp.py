import os
from PIL import Image
import argparse

def convert_png_to_webp(input_path, output_path=None, quality=80):
    """
    Convert a PNG image to WebP format while preserving alpha channel.
    
    Args:
        input_path (str): Path to input PNG file
        output_path (str, optional): Path for output WebP file. If None, uses same name as input
        quality (int): Quality of WebP image (0-100), default 80
    """
    try:
        # Open the PNG image
        with Image.open(input_path) as img:
            # If no output path specified, create one
            if output_path is None:
                output_path = os.path.splitext(input_path)[0] + '.webp'
            
            # Convert and save as WebP
            img.save(output_path, 'WEBP', quality=quality, lossless=False)
            print(f"Successfully converted {input_path} to {output_path}")
            
    except Exception as e:
        print(f"Error converting {input_path}: {str(e)}")

def process_directory(directory_path, quality=80):
    """
    Convert all PNG files in a directory to WebP format.
    
    Args:
        directory_path (str): Path to directory containing PNG files
        quality (int): Quality of WebP images (0-100)
    """
    for filename in os.listdir(directory_path):
        if filename.lower().endswith('.png'):
            input_path = os.path.join(directory_path, filename)
            convert_png_to_webp(input_path, quality=quality)

def main():
    parser = argparse.ArgumentParser(description='Convert PNG images to WebP format while preserving alpha channel')
    parser.add_argument('input', help='Input PNG file or directory')
    parser.add_argument('-q', '--quality', type=int, default=80, help='WebP quality (0-100), default: 80')
    parser.add_argument('-o', '--output', help='Output WebP file (only for single file conversion)')
    
    args = parser.parse_args()
    
    if os.path.isfile(args.input):
        convert_png_to_webp(args.input, args.output, args.quality)
    elif os.path.isdir(args.input):
        if args.output:
            print("Warning: Output path is ignored when processing a directory")
        process_directory(args.input, args.quality)
    else:
        print(f"Error: {args.input} is not a valid file or directory")

if __name__ == '__main__':
    main()
