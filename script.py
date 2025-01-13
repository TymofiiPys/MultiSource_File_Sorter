import os
import re
from datetime import datetime
import exifread
from pathlib import Path
from typing import Dict, Tuple

def extract_date_from_android_filename(filename: str) -> datetime:
    """Extract date from Android-style filenames (IMG_/VID_/PXL_YYYYMMDD_HHMMSS*)."""
    match = re.match(r'(?:IMG|VID|PXL)_(\d{8})_(\d{6})', filename)
    if match:
        date_str, time_str = match.groups()
        return datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
    return None

def extract_date_from_heic_metadata(filepath: str) -> datetime:
    """Extract date from HEIC file metadata."""
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f)
        # Try different possible tag names for capture date
        date_tags = [
            'EXIF DateTimeOriginal',
            'Image DateTime',
            'Date of capture',
            'Дата зйомки',  # Ukrainian
            'Media created',
            'Носій створено'  # Ukrainian
        ]
        
        for tag in date_tags:
            if tag in tags:
                try:
                    # Assuming date format is "YYYY:MM:DD HH:MM:SS"
                    date_str = str(tags[tag])
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
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
    
    # Try Android/Pixel style filename
    android_date = extract_date_from_android_filename(filename)
    if android_date:
        return android_date, 'android'
    
    # For HEIC/MOV files
    if extension.endswith(('.heic', '.mov')):
        metadata_date = extract_date_from_heic_metadata(filepath)
        if metadata_date:
            return metadata_date, 'ios'
    
    return None, 'unknown'

def sort_and_rename_files(input_dir: str, output_dir: str) -> None:
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
    for index, (filepath, _, original_filename) in enumerate(files_data, start=1):
        extension = os.path.splitext(original_filename)[1]
        new_filename = f"{index}{extension}"
        new_filepath = os.path.join(output_dir, new_filename)
        
        # Copy file to new location with new name
        with open(filepath, 'rb') as src, open(new_filepath, 'wb') as dst:
            dst.write(src.read())
        
        print(f"Processed: {original_filename} -> {new_filename}")

def main():
    input_dir = "input_folder"  # Replace with your input folder path
    output_dir = "sorted_media"  # Replace with your output folder path
    
    print("Starting media file sorting...")
    sort_and_rename_files(input_dir, output_dir)
    print("Sorting complete!")

if __name__ == "__main__":
    main()