# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a video processing tool that removes non-English audio tracks from video files. The project consists of a single Python script (`video_processor.py`) that uses ffmpeg to analyze and modify video files, containerized with Docker for easy deployment.

## Core Architecture

- **Single-file Python application**: `video_processor.py` contains all functionality
- **ffmpeg dependency**: Uses ffprobe for analysis and ffmpeg for processing
- **Docker containerized**: Designed to run in containers with volume mounts
- **Logging system**: Comprehensive logging to files and console
- **Safety mechanisms**: Creates backups before processing, restores on failure

## Common Commands

### Docker Operations
```bash
# Build the container
docker build -t video-processor .

# Run dry-run test (logs output to ./logs)
docker run -v /path/to/videos:/videos -v ./logs:/app/logs video-processor /videos --dry-run

# Process files (production, logs output to ./logs)
docker run -v /path/to/videos:/videos -v ./logs:/app/logs video-processor /videos

# With custom video directory and logs
docker run -v /path/to/videos:/videos -v /custom/logs:/app/logs video-processor /videos
```

### Docker Compose Operations
```bash
# Run dry-run via compose
docker-compose run video-processor /videos --dry-run

# Process files via compose
docker-compose run video-processor /videos
```

### Direct Python Execution
```bash
# Run locally (requires ffmpeg installed)
python3 video_processor.py /path/to/videos --dry-run
python3 video_processor.py /path/to/videos --log-dir ./logs
python3 video_processor.py /path/to/videos --log-file custom.log --log-dir /custom/path
```

## Key Implementation Details

### Video Processing Logic
- Recursively scans directories for video files with common extensions
- Uses ffprobe to analyze audio streams in each file
- Skips files with single or no audio tracks
- English track detection via language tags (`en`, `eng`, `english`) and title analysis
- Creates backup before processing, removes on success, restores on failure

### File Structure
- `video_processor.py`: Main application (lines 1-230)
- `Dockerfile`: Container build instructions
- `docker-compose.yaml`: Local development setup
- `test_videos/`: Sample video files for testing
- `logs/`: Directory for persistent log storage

### Output Files
- `audio_processing.log`: Main processing log with detailed operation info
- `no_english_tracks.log`: Files with multiple audio tracks but no English track found
- Both log files are created in the specified log directory (`--log-dir`) or current directory by default

### New Logging Features
- **Enhanced dry-run logging**: Shows exactly which tracks would be kept/removed
- **Detailed processing logs**: Backup creation, ffmpeg commands, success/failure details  
- **Summary statistics**: Final counts of processed files, files without English tracks
- **Configurable log directory**: Use `--log-dir` to specify where all log files are written

## Development Workflow

When modifying this project:
1. Test changes with `--dry-run` flag first
2. Use the test videos in `test_videos/` directory for validation
3. Check both log files after processing
4. Rebuild Docker container after code changes
5. Test with various video formats supported (MP4, MKV, AVI, MOV, etc.)

## ffmpeg Command Structure

The tool uses this ffmpeg command pattern:
```bash
ffmpeg -i backup_file -map 0:v -map 0:{english_track_index} -c:v copy -c:a copy -y output_file
```

This preserves video quality while removing unwanted audio tracks.