FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy the Python script
COPY video_processor.py /app/

# Make the script executable
RUN chmod +x /app/video_processor.py

# Create a directory for the mounted videos
RUN mkdir -p /videos

# Set the default command
ENTRYPOINT ["python3", "/app/video_processor.py"]
CMD ["/videos"]
