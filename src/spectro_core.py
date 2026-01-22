import numpy as np
import subprocess
import json
import os
import sys

# ==========================================
# 1. CONFIGURATION
# ==========================================
class SpectroSettings:
    """Central place for audio/visual settings."""
    def __init__(self, resolution=360, sample_rate=44100, hop_length=64):
        self.resolution = resolution      # Height (Frequency bins)
        self.sample_rate = sample_rate    # Audio Speed (Hz)
        self.hop_length = hop_length      # Horizontal compression (Step size)

        # Derived values
        self.n_fft = (resolution - 1) * 2

# ==========================================
# 2. THE DATA OBJECT
# ==========================================
class SpectroData:
    """
    Holds grayscale pixel data ready for conversion.
    Allows concatenation like: data = video_data + image_data
    """
    def __init__(self, settings):
        self.settings = settings
        self.frames = [] # List of 2D numpy arrays (normalized 0.0-1.0)

    def add_frame(self, frame_np):
        """Adds a single numpy frame."""
        self.frames.append(frame_np)

    def add_gap(self, duration_seconds):
        """Adds a black silence gap."""
        # Calculate width of silence
        samples = int(duration_seconds * self.settings.sample_rate)
        width = int(samples / self.settings.hop_length)
        if width < 1: width = 1

        # Create black frame
        black = np.zeros((self.settings.resolution, width), dtype=np.float32)
        self.frames.append(black)

    def __add__(self, other):
        """Overload '+' operator to merge two SpectroData objects."""
        if not isinstance(other, SpectroData):
            raise TypeError("Can only add SpectroData to SpectroData")

        # Create new merged object
        new_obj = SpectroData(self.settings)
        new_obj.frames = self.frames + other.frames
        return new_obj

    def get_full_stack(self):
        """Returns the single massive numpy array needed for processing."""
        if not self.frames:
            return None
        return np.hstack(self.frames)

# ==========================================
# 3. INGESTORS (FILE READERS)
# ==========================================
class Ingest:
    """Factory methods to create SpectroData objects from files."""

    @staticmethod
    def _get_ffmpeg_cmd(path, width, height, is_video=True):
        """Helper to build FFmpeg command."""
        filters = f'scale={width}:{height},eq=contrast=1.5:saturation=0,format=gray'
        cmd = [
            'ffmpeg', '-v', 'error', '-i', path,
            '-vf', filters,
            '-f', 'rawvideo', '-pix_fmt', 'gray', '-'
        ]
        return cmd

    @classmethod
    def from_image(cls, path, duration, settings):
        """Creates data from a single static image."""
        data = SpectroData(settings)

        if not os.path.exists(path):
            print(f"[Error] File not found: {path}")
            return data

        # Calculate required width based on duration and settings
        total_samples = duration * settings.sample_rate
        width = int(total_samples / settings.hop_length)
        if width < 1: width = 1

        cmd = cls._get_ffmpeg_cmd(path, width, settings.resolution)

        try:
            raw = subprocess.check_output(cmd)
            # Process raw bytes to numpy
            frame = np.frombuffer(raw, dtype=np.uint8)
            frame = frame.reshape((settings.resolution, width))

            # Flip vertical (Spectrogram standard) & Normalize
            frame = np.flipud(frame).astype(np.float32) / 255.0
            data.add_frame(frame)

        except subprocess.CalledProcessError:
            print(f"[Error] Failed to process image: {path}")

        return data

    @classmethod
    def from_image_list(cls, paths, duration_per_image, settings, gap = 0.0):
        """Creates data from a list of images."""
        master_data = SpectroData(settings)

        for path in paths:
            # Create temp object for single image
            img_data = cls.from_image(path, duration_per_image, settings)

            # Merge into master
            master_data = master_data + img_data

            # Optional: Add small gap between slides
            master_data.add_gap(gap)

        return master_data

    @classmethod
    def from_image_folder(cls, folder_path, duration_per_image, settings, gap = 0.0):
        """
        Scans a folder for images, sorts them alphabetically,
        and creates a spectrogram sequence.
        """
        if not os.path.exists(folder_path):
            print(f"[Error] Folder not found: {folder_path}")
            return SpectroData(settings)

        # Define valid extensions
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

        # 1. List all files
        # 2. Filter by extension
        # 3. Create full paths
        images = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(valid_extensions)
        ]

        # 4. Sort Alphabetically
        # using key=str.lower ensures "a.jpg" and "A.jpg" sort naturally
        images = sorted(images, key=str.lower)

        if not images:
            print(f"[Warning] No valid images found in: {folder_path}")
            return SpectroData(settings)

        print(f"[Ingest] Found {len(images)} images in folder '{os.path.basename(folder_path)}'")

        # Reuse the logic we already wrote for lists
        return cls.from_image_list(images, duration_per_image, settings, gap)

    @classmethod
    def from_numpy(cls, path, settings):
        """Loads a raw .npy drawing created by the Painter."""
        data = SpectroData(settings)

        if not os.path.exists(path):
            print(f"[Error] File not found: {path}")
            return data

        try:
            # Load raw array
            # Shape should be (Resolution, Width)
            raw_data = np.load(path)

            # Check resolution match
            if raw_data.shape[0] != settings.resolution:
                print(f"[Warning] Drawing height ({raw_data.shape[0]}) does not match settings ({settings.resolution}). Resizing...")
                # Simple resize logic if needed, or just error out
                # For now, let's assume the user was consistent.

            # Normalize 0-255 -> 0.0-1.0
            frame = raw_data.astype(np.float32) / 255.0

            # Flip Vertical?
            # In the painter, Y=0 is Top. In Spectrogram, Y=0 is Low Freq (Bottom).
            # When we painted, we painted intuitively (Top = High Freq).
            # So we usually DON'T need to flip if the painter logic matched visual intuition.
            # But our previous ingestors flip. Let's try flipping to match standard behavior.
            frame = np.flipud(frame)

            data.add_frame(frame)
            print(f"[Ingest] Loaded drawing: {path} ({raw_data.shape[1]} px wide)")

        except Exception as e:
            print(f"[Error] Failed to load numpy file: {e}")

        return data

    @classmethod
    def from_video(cls, path, settings):
        """Creates data from a video file."""
        data = SpectroData(settings)

        # Get duration/fps to calculate width
        try:
            probe = subprocess.check_output([
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=duration,width,height', '-of', 'json', path
            ])
            meta = json.loads(probe)['streams'][0]
            video_duration = float(meta['duration'])
            aspect = int(meta['width']) / int(meta['height'])
        except:
            print("[Error] Could not probe video.")
            return data

        # Calculate width to fit the exact audio duration
        # Logic: We want video duration == audio duration.
        total_samples = video_duration * settings.sample_rate
        width = int(total_samples / settings.hop_length)

        print(f"[Video] Resizing to {width}x{settings.resolution} to match {video_duration}s audio.")

        cmd = cls._get_ffmpeg_cmd(path, width, settings.resolution)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        bytes_per_frame = width * settings.resolution

        # Read the ENTIRE video as one raw block (since we resized it to be 1 frame effectively)
        # Note: For very long videos, we might want to chunk this.
        try:
            # Streaming reader
            chunk_height = settings.resolution
            chunk_width = width # FFmpeg outputs it as one massive image stream

            while True:
                # Read row by row or small chunks if needed.
                # Since we forced 'scale=width:height', FFmpeg creates ONE massive frame
                # or a stream of frames.
                # Easier approach for video: Read raw stream and reshape.
                raw = process.stdout.read(width * settings.resolution)
                if not raw: break

                frame = np.frombuffer(raw, dtype=np.uint8)
                frame = frame.reshape((settings.resolution, width))
                frame = np.flipud(frame).astype(np.float32) / 255.0
                data.add_frame(frame)
        finally:
            process.stdout.close()
            process.wait()

        return data
