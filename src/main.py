from spectro_core import SpectroSettings, Ingest
from spectro_render import AudioRenderer

def main():
    # 1. Define Settings (Standard Audio)
    # Using 44100Hz and hop_length 64 gives high detail but larger width
    config = SpectroSettings(resolution=360, sample_rate=44100, hop_length=64)

    # 2. Ingest Media
    print("--- Loading Media ---")

    # Load a video
    # video_data = Ingest.from_video("cut.mp4", config)

    # Load images
    # images = ["docs/test/0.jpeg", "docs/test/1.jpeg", "docs/test/2.jpeg", "docs/test/3.jpeg"]
    # slideshow_data = Ingest.from_image_list(images, duration_per_image=3.0, settings=config)
    slideshow_data = Ingest.from_image_folder("docs/IMAGES BIEN", duration_per_image=3.0, settings=config, gap=1)
    #slideshow_data = Ingest.from_numpy("docs/moon.npy", config)

    # Load a specific ending logo
    # logo_data = Ingest.from_image("logo.png", duration=2.0, settings=config)

    # 3. Combine Them (Concatenation)
    # final_data = video_data + slideshow_data + logo_data
    final_data = slideshow_data # Just slideshow for now

    # 4. Render
    renderer = AudioRenderer()
    renderer.render(final_data, "out/final?.wav")

if __name__ == "__main__":
    main()
