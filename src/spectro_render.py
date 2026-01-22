import torch
import torchaudio
import soundfile as sf
import numpy as np
from spectro_core import SpectroData

class AudioRenderer:
    def __init__(self, device=None):
        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Renderer] Using device: {self.device}")

    def render(self, spectro_data: SpectroData, output_path, iterations=32):
        """Converts SpectroData object to WAV file."""

        if not spectro_data.frames:
            print("No data to render.")
            return

        settings = spectro_data.settings

        print("Stacking frames...")
        full_spec = spectro_data.get_full_stack()

        print(f"Processing Matrix: {full_spec.shape}")

        # Prepare Griffin-Lim
        griffin_lim = torchaudio.transforms.GriffinLim(
            n_fft=settings.n_fft,
            hop_length=settings.hop_length,
            n_iter=iterations,
            power=1.0
        ).to(self.device)

        # Convert to Tensor
        spec_tensor = torch.tensor(full_spec).unsqueeze(0).to(self.device)

        print("Reconstructing Audio...")
        with torch.no_grad():
            waveform = griffin_lim(spec_tensor)

        # Save
        audio = waveform.squeeze().cpu().numpy()
        sf.write(output_path, audio, settings.sample_rate)
        print(f"Saved to: {output_path}")
