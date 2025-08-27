#!/usr/bin/env python3

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
import logging
from typing import List, Dict, Optional

# Common video file extensions
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', 
    '.m4v', '.3gp', '.ogv', '.ts', '.mts', '.m2ts'
}

def setup_logging(log_file: str = 'audio_processing.log') -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger('video_processor')
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_video_info(file_path: str) -> Optional[Dict]:
    """Get video file information using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return None
    except json.JSONDecodeError:
        return None

def get_audio_tracks(video_info: Dict) -> List[Dict]:
    """Extract audio track information from video info"""
    audio_tracks = []
    for stream in video_info.get('streams', []):
        if stream.get('codec_type') == 'audio':
            audio_tracks.append({
                'index': stream.get('index'),
                'language': stream.get('tags', {}).get('language', 'und'),
                'title': stream.get('tags', {}).get('title', ''),
                'codec': stream.get('codec_name', ''),
                'channels': stream.get('channels', 0)
            })
    return audio_tracks

def find_english_track(audio_tracks: List[Dict]) -> Optional[int]:
    """Find the English audio track index"""
    # Common English language codes
    english_codes = {'en', 'eng', 'english'}
    
    # First, look for explicitly tagged English tracks
    for track in audio_tracks:
        lang = track['language'].lower()
        if lang in english_codes:
            return track['index']
    
    # If no explicit English tag, check titles for English indicators
    for track in audio_tracks:
        title = track.get('title', '').lower()
        if any(eng_word in title for eng_word in ['english', 'eng']):
            return track['index']
    
    # If still no English track found, return None
    return None

def process_video_file(file_path: str, dry_run: bool, logger: logging.Logger) -> bool:
    """Process a single video file to keep only English audio track"""
    logger.info(f"Processing: {file_path}")
    
    # Get video information
    video_info = get_video_info(file_path)
    if not video_info:
        logger.error(f"Could not get video info for: {file_path}")
        return False
    
    # Get audio tracks
    audio_tracks = get_audio_tracks(video_info)
    
    if len(audio_tracks) <= 1:
        logger.info(f"Skipping (single or no audio track): {file_path}")
        return True
    
    logger.info(f"Found {len(audio_tracks)} audio tracks")
    for track in audio_tracks:
        logger.info(f"  Track {track['index']}: {track['language']} - {track['title']} ({track['codec']})")
    
    # Find English track
    english_track_index = find_english_track(audio_tracks)
    
    if english_track_index is None:
        logger.warning(f"No English audio track found in: {file_path}")
        with open('no_english_tracks.log', 'a') as f:
            f.write(f"{file_path}\n")
            f.write(f"  Audio tracks: {json.dumps(audio_tracks, indent=2)}\n")
            f.write("---\n")
        return True
    
    logger.info(f"English track found at index: {english_track_index}")
    
    if dry_run:
        logger.info(f"DRY RUN: Would remove all audio tracks except index {english_track_index}")
        return True
    
    # Create backup file name
    backup_path = f"{file_path}.backup"
    
    try:
        # Rename original to backup
        os.rename(file_path, backup_path)
        
        # Build ffmpeg command to keep only English audio track
        cmd = [
            'ffmpeg', '-i', backup_path,
            '-map', '0:v',  # Copy all video streams
            '-map', f'0:a:{english_track_index}',  # Copy only the English audio track
            '-c:v', 'copy',  # Copy video without re-encoding
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',  # Overwrite output file
            file_path
        ]
        
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Success - remove backup
            os.remove(backup_path)
            logger.info(f"Successfully processed: {file_path}")
            return True
        else:
            # Error - restore backup
            os.rename(backup_path, file_path)
            logger.error(f"ffmpeg failed for {file_path}: {result.stderr}")
            return False
            
    except Exception as e:
        # Restore backup if it exists
        if os.path.exists(backup_path):
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(backup_path, file_path)
        logger.error(f"Error processing {file_path}: {str(e)}")
        return False

def find_video_files(directory: str) -> List[str]:
    """Find all video files in directory and subdirectories"""
    video_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if Path(file).suffix.lower() in VIDEO_EXTENSIONS:
                video_files.append(os.path.join(root, file))
    return video_files

def main():
    parser = argparse.ArgumentParser(
        description="Remove all audio tracks except English from video files"
    )
    parser.add_argument(
        'directory', 
        help='Directory containing video files to process'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--log-file',
        default='audio_processing.log',
        help='Log file path (default: audio_processing.log)'
    )
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        sys.exit(1)
    
    # Setup logging
    logger = setup_logging(args.log_file)
    
    if args.dry_run:
        logger.info("=== DRY RUN MODE - No changes will be made ===")
    
    logger.info(f"Starting audio track processing in: {args.directory}")
    
    # Find all video files
    video_files = find_video_files(args.directory)
    logger.info(f"Found {len(video_files)} video files")
    
    if not video_files:
        logger.info("No video files found")
        return
    
    # Process each video file
    success_count = 0
    for file_path in video_files:
        if process_video_file(file_path, args.dry_run, logger):
            success_count += 1
    
    logger.info(f"Processing complete: {success_count}/{len(video_files)} files processed successfully")
    
    if not args.dry_run and os.path.exists('no_english_tracks.log'):
        logger.info("Check 'no_english_tracks.log' for files without English audio tracks")

if __name__ == "__main__":
    main()