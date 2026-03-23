"""Audio mood detection — extract audio features and classify mood."""

import logging
import os
import subprocess
import tempfile

import numpy as np

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_path: str | None = None) -> str:
    """Extract audio track from video as mono WAV at 22kHz.

    Args:
        video_path: Path to the video file.
        output_path: Optional destination. If None, uses a temp file.

    Returns:
        Path to the extracted WAV file.
    """
    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix="_audio.wav")
        os.close(fd)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "22050",
        "-ac", "1",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr[-300:]}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
        raise RuntimeError("Audio extraction produced empty output")

    return output_path


def analyze_music_features(audio_path: str) -> dict:
    """Extract musical features that indicate mood.

    Returns dict with tempo, energy, spectral features, MFCCs,
    onset density, dynamic range, and speech/music detection.
    """
    import librosa

    y, sr = librosa.load(audio_path, sr=22050)

    # Check for silence
    rms = librosa.feature.rms(y=y)[0]
    silence_ratio = float(np.mean(rms < 0.01))

    if silence_ratio > 0.9:
        return {"has_audio": False, "silence_ratio": silence_ratio}

    # Tempo (BPM)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = float(np.atleast_1d(tempo)[0])

    # Energy (RMS normalized to 0-1)
    energy = float(np.mean(rms))
    energy_normalized = min(energy / 0.1, 1.0)

    # Spectral features
    spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    spectral_rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=y)))

    # MFCCs (tonal fingerprint)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_means = mfccs.mean(axis=1).tolist()

    # Chroma (pitch/harmony)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_energy = chroma.mean(axis=1).tolist()

    # Onset density (events per second)
    onsets = librosa.onset.onset_detect(y=y, sr=sr)
    duration = librosa.get_duration(y=y, sr=sr)
    onset_density = len(onsets) / max(duration, 1.0)

    # Dynamic range
    rms_db = librosa.amplitude_to_db(rms + 1e-10)
    dynamic_range = float(np.std(rms_db)) / 40.0

    # Simple speech vs music heuristic
    has_speech = zcr > 0.05 and spectral_centroid < 4000
    has_music = onset_density > 1.0 or tempo_val > 60

    return {
        "has_audio": True,
        "tempo": tempo_val,
        "energy": float(energy_normalized),
        "spectral_centroid": spectral_centroid,
        "spectral_rolloff": spectral_rolloff,
        "zero_crossing_rate": zcr,
        "mfcc_means": mfcc_means,
        "chroma_energy": chroma_energy,
        "onset_density": float(onset_density),
        "dynamic_range": float(np.clip(dynamic_range, 0, 1)),
        "has_speech": bool(has_speech),
        "has_music": bool(has_music),
        "silence_ratio": silence_ratio,
    }


def classify_audio_mood(features: dict) -> dict:
    """Classify audio into mood categories based on extracted features.

    Returns dict with primary_mood, secondary_mood, intensity (0-1),
    warmth (0-1), complexity (0-1), and mood_tags.
    """
    if not features.get("has_audio", False):
        return {
            "primary_mood": "neutral",
            "secondary_mood": "calm",
            "intensity": 0.3,
            "warmth": 0.5,
            "complexity": 0.2,
            "mood_tags": ["neutral", "silent"],
        }

    tempo = features["tempo"]
    energy = features["energy"]
    spectral = features["spectral_centroid"]
    onset_density = features["onset_density"]
    dynamic_range = features["dynamic_range"]

    # Intensity: high tempo + high energy + high onset density
    intensity = float(np.clip(
        (tempo / 180) * 0.3 + energy * 0.4 + (onset_density / 8) * 0.3,
        0, 1,
    ))

    # Warmth: lower spectral centroid = warmer, slower tempo = warmer
    warmth = float(np.clip(
        (1 - spectral / 8000) * 0.5 + (1 - tempo / 180) * 0.3 + (1 - energy) * 0.2,
        0, 1,
    ))

    # Complexity: dynamic range + onset variety + energy
    complexity = float(np.clip(
        dynamic_range * 0.5 + (onset_density / 8) * 0.3 + energy * 0.2,
        0, 1,
    ))

    # Classify primary mood
    mood_tags = []

    if intensity > 0.7:
        if warmth > 0.5:
            primary_mood = "epic"
            mood_tags.extend(["epic", "powerful", "triumphant"])
        else:
            primary_mood = "intense"
            mood_tags.extend(["intense", "aggressive", "driving"])
    elif intensity > 0.4:
        if warmth > 0.6:
            primary_mood = "upbeat"
            mood_tags.extend(["upbeat", "positive", "energetic"])
        elif warmth < 0.3:
            primary_mood = "dark"
            mood_tags.extend(["dark", "moody", "atmospheric"])
        else:
            primary_mood = "neutral"
            mood_tags.extend(["balanced", "moderate"])
    else:
        if warmth > 0.6:
            primary_mood = "warm"
            mood_tags.extend(["warm", "gentle", "nostalgic"])
        elif warmth < 0.3:
            primary_mood = "melancholic"
            mood_tags.extend(["sad", "melancholic", "somber"])
        else:
            primary_mood = "calm"
            mood_tags.extend(["calm", "peaceful", "ambient"])

    # Secondary mood
    if features.get("has_speech") and not features.get("has_music"):
        secondary_mood = "conversational"
        mood_tags.append("dialogue")
    elif dynamic_range > 0.5:
        secondary_mood = "dramatic"
        mood_tags.append("dramatic")
    else:
        secondary_mood = "steady"
        mood_tags.append("consistent")

    return {
        "primary_mood": primary_mood,
        "secondary_mood": secondary_mood,
        "intensity": intensity,
        "warmth": warmth,
        "complexity": complexity,
        "mood_tags": mood_tags,
    }
