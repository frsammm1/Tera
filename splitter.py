import os
import subprocess
import glob

class Splitter:
    def __init__(self):
        pass

    def split_file(self, input_file, chunk_size_bytes=2000 * 1024 * 1024): # 2000MB (~1.95GB)
        # Using ffmpeg to split allows for playable parts if it's a video,
        # BUT ffmpeg splitting by size or time without re-encoding is tricky for exact size.
        # However, the user asked for "playable" parts.
        # "segment" muxer is good for this.

        # Check if file exists
        if not os.path.exists(input_file):
            return []

        file_size = os.path.getsize(input_file)
        if file_size <= chunk_size_bytes:
            return [input_file]

        # It's > 2GB.
        # Method 1: 'split' command (binary split) - Not playable usually.
        # Method 2: FFmpeg segment muxer.
        # "part wise me aane ka system rkhna... playable"

        # We'll use ffmpeg segment.
        output_pattern = f"{input_file}_part%03d.mp4" # Assuming mp4 for now, usually it detects

        # Determine duration to split roughly by size? Hard.
        # Safer bet for "playable" and "size limit":
        # Use 'fs' segment option in ffmpeg? No, fs is for single output.
        # Use -fs with iterative calls? Slow.

        # Actually, Telegram supports files up to 2GB.
        # If we just split binary, it won't be playable.
        # If we use ffmpeg -c copy -map 0 -segment_time ... -f segment ...
        # We don't know the bitrate, so segment_time is hard to map to 2GB.

        # Alternative: simple binary split. The first part is playable. Others might not be.
        # User insisted "playable".
        # Let's try to use `mkvmerge` (part of MKVToolNix) if available? Not standard.
        # Let's stick to ffmpeg.
        # Calculate duration.

        try:
            # get duration
            probe = subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_file]
            )
            duration = float(probe)

            # Calculate average bitrate
            bitrate = file_size * 8 / duration

            # Max size bits
            max_size_bits = chunk_size_bytes * 8

            # Segment duration
            segment_duration = max_size_bits / bitrate
            # Reduce slightly to be safe (95%)
            segment_duration = segment_duration * 0.95

            # Run split
            base_name, ext = os.path.splitext(input_file)
            output_pattern = f"{base_name}_part%03d{ext}"

            cmd = [
                "ffmpeg", "-i", input_file,
                "-c", "copy",
                "-map", "0",
                "-f", "segment",
                "-segment_time", str(segment_duration),
                "-reset_timestamps", "1",
                output_pattern
            ]

            subprocess.run(cmd, check=True)

            # Collect parts
            parts = sorted(glob.glob(f"{base_name}_part*{ext}"))
            return parts

        except Exception as e:
            print(f"Error splitting: {e}")
            # Fallback to binary split if ffmpeg fails (or not video)
            return self.binary_split(input_file, chunk_size_bytes)

    def binary_split(self, input_file, chunk_size):
        # Fallback for non-video files or ffmpeg failure
        parts = []
        part_num = 1
        with open(input_file, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                part_name = f"{input_file}.part{part_num}"
                with open(part_name, 'wb') as p:
                    p.write(chunk)
                parts.append(part_name)
                part_num += 1
        return parts

splitter = Splitter()
