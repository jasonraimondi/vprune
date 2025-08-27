# Video Audio Track Processor (VIBE CODE WARNING)

This tool processes video files in a directory tree, removing all audio tracks except the English track. It's designed to clean up video collections with multiple audio tracks.

## Features

- **Recursive Processing**: Scans all subdirectories for video files
- **Multiple Formats**: Supports all common video formats (MP4, MKV, AVI, MOV, etc.)
- **Smart English Detection**: Finds English tracks by language tags and title analysis
- **Safe Processing**: Creates backups and restores on failure
- **Dry Run Mode**: Test what would be changed without making modifications
- **Comprehensive Logging**: Detailed logs of all operations
- **Error Handling**: Logs files without English tracks separately

## Quick Start

### Using Docker (Recommended)

   ```bash
      docker run -it --rm \
         -v "$(pwd)":/videos \
         -v "$(pwd)"/logs:/app/logs \
         -w /app \
         -e LOG_DIR=/app/logs \
         ghcr.io/jasonraimondi/vprune:latest /videos --dry-run
   ```

### Using Docker Compose

1. **Place your videos in a `./videos` directory**

2. **Run dry-run:**
   ```bash
   docker-compose run video-processor /videos --dry-run
   ```

3. **Process files:**
   ```bash
   docker-compose run video-processor /videos
   ```

## Command Line Options

```bash
video_processor.py [-h] [--dry-run] [--log-file LOG_FILE] directory

Arguments:
  directory          Directory containing video files to process

Options:
  -h, --help         Show help message
  --dry-run          Show what would be done without making changes
  --log-file FILE    Log file path (default: audio_processing.log)
```

