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
    logger.setLevel(logging.DEBUG)  # Enable debug level for detailed logging
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
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

def get_video_info(file_path: str, logger: logging.Logger) -> Optional[Dict]:
    """Get video file information using ffprobe"""
    logger.debug(f"[PROBE_START] Analyzing video file: {file_path}")
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        logger.debug(f"[PROBE_COMMAND] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.debug(f"[PROBE_SUCCESS] ffprobe completed successfully for: {file_path}")
        video_info = json.loads(result.stdout)
        logger.debug(f"[PROBE_PARSED] Found {len(video_info.get('streams', []))} streams in: {file_path}")
        return video_info
    except subprocess.CalledProcessError as e:
        logger.error(f"[PROBE_FAILED] ffprobe failed for {file_path}: return code {e.returncode}")
        logger.error(f"[PROBE_STDERR] {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"[PROBE_JSON_ERROR] Failed to parse ffprobe output for {file_path}: {str(e)}")
        return None

def get_audio_tracks(video_info: Dict, logger: logging.Logger, file_path: str) -> List[Dict]:
    """Extract audio track information from video info"""
    logger.debug(f"[AUDIO_EXTRACTION_START] Extracting audio tracks from: {file_path}")
    audio_tracks = []
    for stream in video_info.get('streams', []):
        if stream.get('codec_type') == 'audio':
            track_info = {
                'index': stream.get('index'),
                'language': stream.get('tags', {}).get('language', 'und'),
                'title': stream.get('tags', {}).get('title', ''),
                'codec': stream.get('codec_name', ''),
                'channels': stream.get('channels', 0)
            }
            audio_tracks.append(track_info)
            logger.debug(f"[AUDIO_TRACK_FOUND] Stream {track_info['index']}: lang='{track_info['language']}', title='{track_info['title']}', codec={track_info['codec']}")
    
    logger.info(f"[AUDIO_EXTRACTION_COMPLETE] Found {len(audio_tracks)} audio tracks in: {file_path}")
    return audio_tracks

def find_english_track(audio_tracks: List[Dict], logger: logging.Logger, file_path: str) -> Optional[int]:
    """Find the English audio track index"""
    logger.debug(f"[ENGLISH_SEARCH_START] Searching for English audio track in: {file_path}")
    
    # Common English language codes
    english_codes = {'en', 'eng', 'english'}
    
    # First, look for explicitly tagged English tracks
    logger.debug(f"[ENGLISH_SEARCH_LANG] Checking language tags for English indicators")
    for track in audio_tracks:
        lang = track['language'].lower()
        logger.debug(f"[ENGLISH_SEARCH_LANG_CHECK] Track {track['index']}: language='{lang}'")
        if lang in english_codes:
            logger.info(f"[ENGLISH_FOUND_LANG] English track found by language tag: stream {track['index']} (lang='{lang}')")
            return track['index']
    
    logger.debug(f"[ENGLISH_SEARCH_TITLE] No language tag match, checking titles for English indicators")
    # If no explicit English tag, check titles for English indicators
    for track in audio_tracks:
        title = track.get('title', '').lower()
        logger.debug(f"[ENGLISH_SEARCH_TITLE_CHECK] Track {track['index']}: title='{title}'")
        if any(eng_word in title for eng_word in ['english', 'eng']):
            logger.info(f"[ENGLISH_FOUND_TITLE] English track found by title: stream {track['index']} (title='{track['title']}')")
            return track['index']
    
    logger.warning(f"[ENGLISH_NOT_FOUND] No English audio track detected in: {file_path}")
    logger.debug(f"[ENGLISH_NOT_FOUND_DETAIL] Available tracks: {[f\"stream {t['index']} (lang='{t['language']}', title='{t['title']}')\" for t in audio_tracks]}")
    return None

def process_video_file(file_path: str, dry_run: bool, logger: logging.Logger) -> bool:
    """Process a single video file to keep only English audio track"""
    logger.info(f"[FILE_PROCESS_START] Processing: {file_path}")
    
    # Get video information
    video_info = get_video_info(file_path, logger)
    if not video_info:
        logger.error(f"[FILE_PROCESS_FAILED] Could not get video info for: {file_path}")
        return False
    
    # Get audio tracks
    audio_tracks = get_audio_tracks(video_info, logger, file_path)
    
    if len(audio_tracks) <= 1:
        logger.info(f"[FILE_SKIP_SINGLE_TRACK] Skipping file with {len(audio_tracks)} audio track(s): {file_path}")
        return True
    
    logger.info(f"[FILE_MULTI_TRACK] File has {len(audio_tracks)} audio tracks, proceeding with analysis")
    for track in audio_tracks:
        logger.info(f"[TRACK_INFO] Stream {track['index']}: lang='{track['language']}', title='{track['title']}', codec={track['codec']}, channels={track['channels']}")
    
    # Find English track
    english_track_index = find_english_track(audio_tracks, logger, file_path)
    
    if english_track_index is None:
        logger.warning(f"[NO_ENGLISH_TRACK] No English audio track found in: {file_path}")
        logger.info(f"[NO_ENGLISH_LOG] Adding to no_english_tracks.log: {file_path}")
        with open('no_english_tracks.log', 'a') as f:
            f.write(f"[NO_ENGLISH_ENTRY] {file_path}\n")
            f.write(f"[NO_ENGLISH_TRACKS] Audio tracks: {json.dumps(audio_tracks, indent=2)}\n")
            f.write("[NO_ENGLISH_SEPARATOR] ---\n")
        return True
    
    logger.info(f"[ENGLISH_TRACK_SELECTED] English track selected: stream {english_track_index}")
    
    if dry_run:
        logger.info(f"[DRY_RUN_ACTION] Would remove all audio tracks except stream {english_track_index} from: {file_path}")
        return True
    
    # Create backup file name
    backup_path = f"{file_path}.backup"
    logger.info(f"[BACKUP_CREATE] Creating backup: {backup_path}")
    
    try:
        # Rename original to backup
        os.rename(file_path, backup_path)
        logger.debug(f"[BACKUP_SUCCESS] Original file backed up successfully")
        
        # Build ffmpeg command to keep only English audio track
        cmd = [
            'ffmpeg', '-i', backup_path,
            '-map', '0:v',  # Copy all video streams
            '-map', f'0:{english_track_index}',  # Copy only the English audio track by absolute stream index
            '-c:v', 'copy',  # Copy video without re-encoding
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-y',  # Overwrite output file
            file_path
        ]
        
        logger.info(f"[FFMPEG_START] Running ffmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Success - remove backup
            os.remove(backup_path)
            logger.info(f"[FFMPEG_SUCCESS] Successfully processed and removed backup: {file_path}")
            logger.debug(f"[FFMPEG_OUTPUT] {result.stdout}")
            return True
        else:
            # Error - restore backup
            logger.error(f"[FFMPEG_FAILED] ffmpeg failed with return code {result.returncode}")
            logger.error(f"[FFMPEG_STDERR] {result.stderr}")
            logger.info(f"[BACKUP_RESTORE] Restoring original file from backup")
            os.rename(backup_path, file_path)
            logger.error(f"[BACKUP_RESTORED] Original file restored due to ffmpeg failure: {file_path}")
            return False
            
    except OSError as e:
        # File operation error - restore backup if it exists
        logger.error(f"[FILE_OP_ERROR] File operation failed: {str(e)}")
        if os.path.exists(backup_path):
            logger.info(f"[BACKUP_RESTORE_EMERGENCY] Attempting emergency backup restore")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                os.rename(backup_path, file_path)
                logger.info(f"[BACKUP_RESTORED_EMERGENCY] Emergency backup restore successful")
            except Exception as restore_error:
                logger.critical(f"[BACKUP_RESTORE_FAILED] Emergency backup restore failed: {str(restore_error)}")
        return False
    except Exception as e:
        # General error - restore backup if it exists
        logger.error(f"[GENERAL_ERROR] Unexpected error processing {file_path}: {str(e)}")
        if os.path.exists(backup_path):
            logger.info(f"[BACKUP_RESTORE_GENERAL] Attempting backup restore after general error")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                os.rename(backup_path, file_path)
                logger.info(f"[BACKUP_RESTORED_GENERAL] Backup restore after general error successful")
            except Exception as restore_error:
                logger.critical(f"[BACKUP_RESTORE_FAILED_GENERAL] Backup restore after general error failed: {str(restore_error)}")
        return False

def find_video_files(directory: str, logger: logging.Logger) -> List[str]:
    """Find all video files in directory and subdirectories"""
    logger.info(f"[DISCOVERY_START] Scanning for video files in: {directory}")
    video_files = []
    scanned_dirs = 0
    
    for root, dirs, files in os.walk(directory):
        scanned_dirs += 1
        logger.debug(f"[DISCOVERY_DIR] Scanning directory: {root}")
        
        for file in files:
            file_ext = Path(file).suffix.lower()
            if file_ext in VIDEO_EXTENSIONS:
                full_path = os.path.join(root, file)
                video_files.append(full_path)
                logger.debug(f"[DISCOVERY_FOUND] Video file found: {full_path}")
    
    logger.info(f"[DISCOVERY_COMPLETE] Scanned {scanned_dirs} directories, found {len(video_files)} video files")
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
    
    logger.info(f"[SESSION_START] Starting video audio track processing session")
    logger.info(f"[SESSION_CONFIG] Target directory: {args.directory}")
    logger.info(f"[SESSION_CONFIG] Dry run mode: {args.dry_run}")
    logger.info(f"[SESSION_CONFIG] Log file: {args.log_file}")
    
    if args.dry_run:
        logger.info("[SESSION_MODE] === DRY RUN MODE - No changes will be made ===")
    
    logger.info(f"[DISCOVERY_INIT] Initializing video file discovery in: {args.directory}")
    
    # Find all video files
    video_files = find_video_files(args.directory, logger)
    
    if not video_files:
        logger.warning("[SESSION_NO_FILES] No video files found in the specified directory")
        logger.info("[SESSION_END] Session completed - no files to process")
        return
    
    logger.info(f"[SESSION_FILES] Ready to process {len(video_files)} video files")
    
    # Process each video file
    success_count = 0
    error_count = 0
    skip_count = 0
    
    for i, file_path in enumerate(video_files, 1):
        logger.info(f"[SESSION_PROGRESS] Processing file {i}/{len(video_files)}")
        
        result = process_video_file(file_path, args.dry_run, logger)
        if result:
            success_count += 1
        else:
            error_count += 1
    
    logger.info(f"[SESSION_COMPLETE] Processing session completed")
    logger.info(f"[SESSION_STATS] Total files: {len(video_files)}")
    logger.info(f"[SESSION_STATS] Successful: {success_count}")
    logger.info(f"[SESSION_STATS] Errors: {error_count}")
    
    if not args.dry_run and os.path.exists('no_english_tracks.log'):
        logger.info("[SESSION_NO_ENGLISH] Some files had no English tracks - check 'no_english_tracks.log'")
    
    if error_count > 0:
        logger.warning(f"[SESSION_WARNINGS] {error_count} files had processing errors - check logs for details")
    
    logger.info("[SESSION_END] Session completed successfully")

if __name__ == "__main__":
    main()