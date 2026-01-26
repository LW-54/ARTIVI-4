# ARTIVI-4: Spectrogram-to-Audio Engine

ARTIVI-4 is a Python-based engine that converts visual data (images, videos, or hand-painted spectrograms) into audio. It treats visual pixels as spectral magnitude data and reconstructs the audio signal using the Griffin-Lim algorithm.

## 🚀 Features

* **Multi-Format Ingest:** Convert images (`.jpg`, `.png`), video files (`.mp4`), or raw numpy arrays into audio.
* **SpectroPainter GUI:** A Tkinter-based drawing tool to manually paint sound with pitch and rhythm snapping grids.
* **Real-Time Visualizer:** A set of FFmpeg commands to view audio steganography live from a microphone.
* **Griffin-Lim Reconstruction:** Uses `torchaudio` and GPU acceleration (if available) for fast phase reconstruction.

## 📂 Project Structure

* `main.py`: The entry point script to define settings, load media, and trigger the render.
* `spectro_core.py`: Contains configuration (`SpectroSettings`), data structures (`SpectroData`), and file ingestors (`Ingest`).
* `spectro_render.py`: The audio rendering engine using PyTorch.
* `spectro_paint.py`: A standalone GUI tool for drawing spectrograms.

## 📡 Real-Time Visualization

To view the spectrogram live (Audacity-style) from your microphone, you can use ffmpeg with a low-latency UDP stream architecture. This bypasses standard buffering to provide smooth 60 FPS playback.

**1. Start the Receiver (The Window)**
Run this in your first terminal window. It will wait for the signal.

```powershell
ffplay -fflags nobuffer -flags low_delay -framedrop -i udp://127.0.0.1:1234?listen

```

**2. Start the Sender (The Microphone)**
Run this in a second terminal window.
*Note: Replace `YOUR_DEVICE_ID` with your actual microphone identifier (find it using `ffmpeg -list_devices true -f dshow -i dummy`).*

```powershell
ffmpeg -f dshow -rtbufsize 100M -i audio="YOUR_DEVICE_ID" -filter_complex "[0:a]pan=1c|c0=c0+c1,volume=3.0,showspectrum=s=1280x640:slide=scroll:mode=combined:color=magma:scale=lin:overlap=0.85:win_func=hann:stop=20000,fps=60,format=yuv420p[v]" -map "[v]" -c:v mpeg2video -b:v 10M -f mpegts udp://127.0.0.1:1234?pkt_size=1316

```

* **Zoom/Stretch:** Adjust `overlap=0.85` (Higher = More Zoom/Stretch).
* **Brightness:** Adjust `volume=3.0`.
* **Theme:** Uses `color=magma` to match the "Roseus" aesthetic.

## ▶️ Usage (Python Generation)

### 1. Generating Audio from Media

Edit `main.py` to define your input sources.

**Example: Convert a folder of images into a slideshow audio track**

```python
from spectro_core import SpectroSettings, Ingest
from spectro_render import AudioRenderer

def main():
    # 1. Config: Higher resolution = Higher max frequency
    config = SpectroSettings(resolution=360, sample_rate=44100, hop_length=64)

    # 2. Ingest: Load a folder of images, each lasting 3 seconds
    slideshow = Ingest.from_image_folder(
        "docs/IMAGES BIEN", 
        duration_per_image=3.0, 
        settings=config, 
        gap=1.0 # 1 second silence between images
    )

    # 3. Render
    renderer = AudioRenderer()
    renderer.render(slideshow, "out/final_audio.wav")

if __name__ == "__main__":
    main()

```

Run the script:

```bash
python main.py

```

### 2. Painting Sound (`spectro_paint.py`)

Launch the painter to draw your own frequencies manually.

```bash
python spectro_paint.py

```

* **Left Click** Paint frequencies.
* **Pitch (Y) Grid:** Snap drawing to specific frequency bands.
* **Rhythm (X) Grid:** Snap drawing to time intervals.
* **Save:** Export as `.npy` (for the engine) or `.png` (for viewing).



## ⚙️ Configuration Details (`SpectroSettings`)

| Parameter | Default | Description |
| --- | --- | --- |
| `resolution` | `360` | Height of the image. Corresponds to frequency bins. Higher = more frequency detail but slower processing. |
| `sample_rate` | `44100` | Audio sampling rate in Hz. |
| `hop_length` | `64` | Horizontal pixel width. Lower values = higher time resolution (pixels represent less time). |

## 📝 Technical Notes

* **Video Ingest:** The `Ingest.from_video` method squashes video frames to match the exact duration of the audio, treating the video timeline as the X-axis of the spectrogram.
* **Image Scaling:** Images are automatically resized and converted to grayscale. Vertical flips are handled automatically to match standard spectrogram orientation (Low freq at bottom).

