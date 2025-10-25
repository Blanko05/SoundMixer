# mixer.py
from pedalboard.io import AudioFile
import numpy as np

def mix_stereo(left_path, right_path, output_path="mixed.wav"):
    """Mix two audio files into stereo"""
    
    with AudioFile(left_path) as f:
        left = f.read(f.frames)
        sr = f.samplerate
    
    with AudioFile(right_path) as f:
        right = f.read(f.frames)
    
    # Convert to mono
    if left.shape[0] > 1:
        left = left.mean(axis=0, keepdims=True)
    if right.shape[0] > 1:
        right = right.mean(axis=0, keepdims=True)
    
    # Loop shorter
    max_len = max(left.shape[1], right.shape[1])
    left = np.tile(left, int(np.ceil(max_len / left.shape[1])))[:, :max_len]
    right = np.tile(right, int(np.ceil(max_len / right.shape[1])))[:, :max_len]
    
    # Stereo
    stereo = np.vstack([left, right])
    
    output_mp3 = output_path.replace('.wav', '.mp3')
    with AudioFile(output_mp3, 'w', sr, num_channels=2) as f:
        f.write(stereo)
    
    return output_path

if __name__ == "__main__":
    result = mix_stereo("song1.mp3", "song2.mp3", "output.wav")
    print(f"Mixed: {result}")