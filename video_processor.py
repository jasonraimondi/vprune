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
    
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
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

def find_english_tracks(audio_tracks: List[Dict]) -> List[int]:
    """Find all English audio track indices"""
    # Common English language codes
    english_codes = {'en', 'eng', 'english'}
    english_track_indices = []
    
    # First, look for explicitly tagged English tracks
    for track in audio_tracks:
        lang = track['language'].lower()
        if lang in english_codes:
            english_track_indices.append(track['index'])
    
    # If no explicit English tags found, check titles for English indicators
    if not english_track_indices:
        for track in audio_tracks:
            title = track.get('title', '').lower()
            if any(eng_word in title for eng_word in ['english', 'eng']):
                english_track_indices.append(track['index'])
    
    return english_track_indices

def process_video_file(file_path: str, dry_run: bool, logger: logging.Logger, no_english_log: str) -> bool:
    """Process a single video file to keep only English audio tracks"""
    logger.info(f"Processing: {file_path}")
    
    # Get video information
    video_info = get_video_info(file_path)
    if not video_info:
        logger.error(f"Could not get video info for: {file_path}")
        return False
    
    # Get audio tracks
    audio_tracks = get_audio_tracks(video_info)
    
    if len(audio_tracks) <= 1:
        if len(audio_tracks) == 0:
            logger.info(f"Skipping (no audio tracks): {file_path}")
        else:
            logger.info(f"Skipping (only one audio track): {file_path}")
        return True
    
    logger.info(f"Found {len(audio_tracks)} audio tracks")
    for track in audio_tracks:
        logger.info(f"  Track {track['index']}: {track['language']} - {track['title']} ({track['codec']})")
    
    # Find English tracks
    english_track_indices = find_english_tracks(audio_tracks)
    
    if not english_track_indices:
        logger.warning(f"No English audio tracks found in: {file_path}")
        with open(no_english_log, 'a') as f:
            f.write(f"{file_path}\n")
            f.write(f"  Audio tracks: {json.dumps(audio_tracks, indent=2)}\n")
            f.write("---\n")
        return True
    
    logger.info(f"English tracks found at indices: {english_track_indices}")
    
    if dry_run:
        tracks_to_remove = [track['index'] for track in audio_tracks if track['index'] not in english_track_indices]
        logger.info(f"DRY RUN: Would keep {len(english_track_indices)} English tracks at indices: {english_track_indices}")
        logger.info(f"DRY RUN: Would remove {len(tracks_to_remove)} audio tracks: {tracks_to_remove}")
        logger.info(f"DRY RUN: File would be processed and overwritten: {file_path}")
        return True
    
    # Create backup file name
    backup_path = f"{file_path}.backup"
    
    try:
        # Log processing start
        tracks_to_remove = [track['index'] for track in audio_tracks if track['index'] not in english_track_indices]
        logger.info(f"Processing file: {file_path}")
        logger.info(f"Keeping {len(english_track_indices)} English tracks at indices: {english_track_indices}")
        logger.info(f"Removing {len(tracks_to_remove)} audio tracks: {tracks_to_remove}")
        
        # Rename original to backup
        logger.info(f"Creating backup: {backup_path}")
        os.rename(file_path, backup_path)
        
        # Build ffmpeg command to keep all English audio tracks
        cmd = [
            'ffmpeg', '-i', backup_path,
            '-map', '0:v',  # Copy all video streams
        ]
        
        # Add mapping for each English audio track
        for track_index in english_track_indices:
            cmd.extend(['-map', f'0:{track_index}'])
        
        cmd.extend([
            '-c:v', 'copy',  # Copy video without re-encoding
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',  # Overwrite output file
            file_path
        ])
        
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Success - remove backup
            os.remove(backup_path)
            logger.info(f"Successfully processed and removed backup: {file_path}")
            logger.info(f"File now contains {len([stream for stream in video_info.get('streams', []) if stream.get('codec_type') == 'video'])} video stream(s) and {len(english_track_indices)} audio stream(s)")
            return True
        else:
            # Error - restore backup
            logger.error(f"ffmpeg failed, restoring backup...")
            os.rename(backup_path, file_path)
            logger.error(f"ffmpeg error for {file_path}: {result.stderr}")
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
        description="Remove all non-English audio tracks from video files, keeping all English tracks"
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
    parser.add_argument(
        '--log-dir',
        help='Log directory path (overrides log-file directory)'
    )
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        sys.exit(1)
    
    # Determine log directory from args, environment, or current directory
    log_dir = args.log_dir or os.environ.get('LOG_DIR')
    
    # Determine log file path
    log_file = args.log_file
    if log_dir:
        log_file = os.path.join(log_dir, os.path.basename(args.log_file))
    
    # Determine no-english log file path
    no_english_log = 'no_english_tracks.log'
    if log_dir:
        no_english_log = os.path.join(log_dir, 'no_english_tracks.log')
    
    # Setup logging
    logger = setup_logging(log_file)
    
    if args.dry_run:
        logger.info("=== DRY RUN MODE - No changes will be made ===")
    
    logger.info(f"Starting audio track processing in: {args.directory}")
    logger.info(f"Log files will be written to: {os.path.dirname(log_file)}")
    
    # Find all video files
    video_files = find_video_files(args.directory)
    logger.info(f"Found {len(video_files)} video files to scan")
    
    # Log supported extensions
    logger.info(f"Scanning for files with extensions: {', '.join(sorted(VIDEO_EXTENSIONS))}")
    
    if not video_files:
        logger.info("No video files found")
        return
    
    # Process each video file
    success_count = 0
    for file_path in video_files:
        if process_video_file(file_path, args.dry_run, logger, no_english_log):
            success_count += 1
    
    logger.info("=" * 50)
    logger.info(f"Processing complete: {success_count}/{len(video_files)} files processed successfully")
    
    if args.dry_run:
        logger.info("DRY RUN COMPLETE - No files were modified")
    else:
        if os.path.exists(no_english_log):
            with open(no_english_log, 'r') as f:
                no_english_count = len([line for line in f if line.strip() and not line.startswith('  ') and line != '---\n'])
            logger.info(f"Files without English tracks: {no_english_count} (see '{no_english_log}')")
        else:
            logger.info("All processed files had identifiable English audio tracks")
        
        logger.info(f"All log files saved to: {os.path.dirname(log_file)}")

if __name__ == "__main__":
    main()