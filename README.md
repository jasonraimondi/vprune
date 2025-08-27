# Video Audio Track Processor

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

1. **Build the container:**
   ```bash
   docker build -t video-processor .
   ```

2. **Run with dry-run to test:**
   ```bash
   docker run -v /path/to/your/videos:/videos video-processor /videos --dry-run
   ```

3. **Process files (removes backup after success):**
   ```bash
   docker run -v /path/to/your/videos:/videos video-processor /videos
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

## How It Works

1. **Discovery**: Recursively finds all video files in the specified directory
2. **Analysis**: Uses `ffprobe` to analyze audio tracks in each file
3. **Filtering**: Skips files with single or no audio tracks
4. **English Detection**: Looks for English tracks using:
   - Language tags (`en`, `eng`, `english`)
   - Title analysis for English keywords
5. **Processing**: Uses `ffmpeg` to create new file with only English audio
6. **Safety**: Creates backup, processes, then removes backup on success

## File Outputs

- **`audio_processing.log`**: Main processing log
- **`no_english_tracks.log`**: Files that have multiple audio tracks but no English track found

## Supported Video Formats

- MP4, MKV, AVI, MOV, WMV, FLV, WebM
- M4V, 3GP, OGV, TS, MTS, M2TS

## Error Handling

- Backup files are created before processing
- Original files are restored if processing fails
- Files without English tracks are logged but not modified
- Network-accessible files should be copied locally first

## Example Usage

### Dry Run Test
```bash
# Test what would happen
docker run -v /media/movies:/videos video-processor /videos --dry-run
```

### Process All Files
```bash
# Actually process files  
docker run -v /media/movies:/videos video-processor /videos
```

### Custom Log Location
```bash
# Use custom log file
docker run -v /media/movies:/videos -v /logs:/app/logs \
  video-processor /videos --log-file /app/logs/processing.log
```

## Notes

- Processing can take time for large files as video is copied
- Audio is copied without re-encoding to maintain quality
- Only files with multiple audio tracks are modified
- The tool preserves all video streams and metadata
- Make sure you have enough disk space (files are temporarily duplicated)

## Troubleshooting

- **Permission Issues**: Ensure the mounted directory has proper read/write permissions
- **Space Issues**: Ensure enough free space (files are temporarily doubled)
- **Format Issues**: Check `audio_processing.log` for specific ffmpeg errors
- **Missing English**: Check `no_english_tracks.log` for files that need manual review