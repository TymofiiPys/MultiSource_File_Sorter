import os
import re
from datetime import datetime
import win32com.client
from pathlib import Path
from typing import Dict, Tuple
from tkinter import filedialog

shell = win32com.client.Dispatch("Shell.Application")
trans_table = {ord('\u200e') : None, ord('\u200f') : None}

def extract_seconds_from_filename(filename: str) -> int:
    """Extract seconds from PXL/IMG/VID filename format."""
    match = re.match(r'(?:PXL|IMG|VID)_\d{8}_(\d{2})(\d{2})(\d{2})', filename)
    if match:
        _, _, seconds = match.groups()
        return int(seconds)
    return 0

def extract_date_from_android_filename(filename: str) -> datetime:
    """Extract date from Android-style filenames (IMG_/VID_/PXL_YYYYMMDD_HHMMSS*)."""
    match = re.match(r'(?:IMG|VID|PXL)_(\d{8})_(\d{6})', filename)
    if match:
        date_str, time_str = match.groups()
        return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
    return None

def extract_date_from_ios_and_pxl_metadata(filepath: str) -> datetime:
    """Extract date from Windows file metadata."""
    try:
        folder = shell.NameSpace(os.path.dirname(filepath))
        file_item = folder.ParseName(os.path.basename(filepath))
        
        # Use specific indices based on file type
        extension = os.path.splitext(filepath)[1].lower()
        # Index 12 for images (Date taken), 208 for videos (Media created)
        index = 208 if extension in ['.mov', '.mp4'] else 12
        
        date_str = folder.GetDetailsOf(file_item, index)[1:].translate(trans_table)
        if date_str:
            datetime_obj = datetime.strptime(date_str, "%d.%m.%Y %H:%M")  
            if datetime_obj:
                # For Pixel files, add seconds from filename
                if os.path.basename(filepath).startswith('PXL_'):
                    seconds = extract_seconds_from_filename(os.path.basename(filepath))
                    datetime_obj = datetime_obj.replace(second=seconds)
                return datetime_obj
        return None
    except Exception as e:
        print(f"Error reading metadata for {filepath}: {e}")
        return None

def get_file_creation_time(filepath: str) -> Tuple[datetime, str]:
    """
    Get creation time and source type for a given file.
    Returns tuple of (datetime, source_type).
    """
    filename = os.path.basename(filepath)
    extension = filename.lower()
    
    # Skip PNG and JPG files with IMG_ prefix
    if re.match(r'IMG_\d+\.(PNG|JPG)$', filename, re.IGNORECASE):
        return None, 'skip'
    
    # Handle Pixel files with metadata + filename seconds
    if filename.startswith('PXL_'):
        metadata_date = extract_date_from_ios_and_pxl_metadata(filepath)
        if metadata_date:
            return metadata_date, 'pixel'

    # Try Android/Pixel style filename (non-Pixel)
    android_date = extract_date_from_android_filename(filename)
    if android_date:
        return android_date, 'android'
    
    # For HEIC/MOV files
    if extension.endswith(('.heic', '.mov')):
        metadata_date = extract_date_from_ios_and_pxl_metadata(filepath)
        if metadata_date:
            return metadata_date, 'ios'
    
    return None, 'unknown'

def get_unique_filepath(filepath: str) -> str:
    """
    Generate a unique filepath by adding _N to the filename if it already exists.
    """
    if not os.path.exists(filepath):
        return filepath
    
    directory = os.path.dirname(filepath)
    filename, extension = os.path.splitext(os.path.basename(filepath))
    counter = 1
    
    while True:
        new_filepath = os.path.join(directory, f"{filename}_{counter}{extension}")
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1


def sort_and_rename_files(input_dir: str, output_dir: str, tag: str) -> None:
    """
    Sort files by creation date and rename them sequentially.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Collect all files and their creation times
    files_data = []
    for filename in os.listdir(input_dir):
        filepath = os.path.join(input_dir, filename)
        if not os.path.isfile(filepath):
            continue
            
        creation_time, source = get_file_creation_time(filepath)
        if source == 'skip':
            print(f"Skipping {filename} (manual processing required)")
            continue
        if creation_time:
            files_data.append((filepath, creation_time, filename))
        else:
            print(f"Warning: Could not determine creation time for {filename}")
    
    # Sort files by creation time
    files_data.sort(key=lambda x: x[1])
    
    # Rename and copy files
    for index, (filepath, creation_time, original_filename) in enumerate(files_data, 1):
        extension = os.path.splitext(original_filename)[1]
        time_str = creation_time.strftime("%Y%m%d_%H%M%S")
        new_filename = f"{time_str}_{tag}{extension}"
        new_filepath = os.path.join(output_dir, new_filename)
        new_filepath = get_unique_filepath(new_filepath)

        # Copy file to new location with new name
        with open(filepath, 'rb') as src, open(new_filepath, 'wb') as dst:
            print("Copying file (", index, "/", len(files_data), "): ", original_filename, "...", sep="")
            dst.write(src.read())
        
        print(f"Processed: {original_filename} -> {new_filename}")

def main():
    input_dir = filedialog.askdirectory(title="Choose input folder path")
    print("Selected input directory:", input_dir)

    output_dir = filedialog.askdirectory()
    print("Selected output directory:", output_dir)
    tag = input("Enter a tag which will appear in filenames or leave an empty line: ")
    print()
    print("Starting media file sorting...")
    # sort_and_rename_files(input_dir, output_dir, tag="yarik")
    print("Sorting complete!")

if __name__ == "__main__":
    main()