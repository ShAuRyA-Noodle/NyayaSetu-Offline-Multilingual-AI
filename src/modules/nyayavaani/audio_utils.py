"""
Audio utilities — file handling, validation, conversion.
"""

import os
import time
import uuid
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def save_upload_audio(audio_bytes: bytes, upload_dir: Path, extension: str = "webm") -> Path:
    """Save uploaded audio to disk with unique filename."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{int(time.time())}_{uuid.uuid4().hex[:8]}.{extension}"
    filepath = upload_dir / filename
    filepath.write_bytes(audio_bytes)
    logger.info(f"Saved audio upload: {filepath} ({len(audio_bytes)} bytes)")
    return filepath


def validate_audio_file(filepath: Path, max_size_bytes: int, max_duration_seconds: int) -> Optional[str]:
    """Validate audio file. Returns error message or None if valid."""
    if not filepath.exists():
        return "Audio file not found"
    size = filepath.stat().st_size
    if size > max_size_bytes:
        return f"Audio file too large: {size} bytes (max {max_size_bytes})"
    if size == 0:
        return "Audio file is empty"
    duration = get_audio_duration(filepath)
    if duration and duration > max_duration_seconds:
        return f"Audio too long: {duration:.0f}s (max {max_duration_seconds}s)"
    return None


def get_audio_duration(filepath: Path) -> Optional[float]:
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(filepath)],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    # Fallback: estimate from file size (~16kbps for webm)
    try:
        size = filepath.stat().st_size
        return size / 2000  # rough estimate
    except Exception:
        return None


def convert_to_wav(input_path: Path, output_dir: Path) -> Path:
    """Convert audio to 16kHz mono WAV using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / f"{input_path.stem}.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(input_path), "-ar", "16000",
             "-ac", "1", "-f", "wav", str(wav_path)],
            capture_output=True, timeout=30, check=True,
        )
        return wav_path
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logger.warning(f"ffmpeg conversion failed: {e}. Using original file.")
        return input_path


def cleanup_old_audio(directory: Path, max_age_hours: int = 1) -> int:
    """Remove audio files older than max_age_hours. Returns count deleted."""
    if not directory.exists():
        return 0
    cutoff = time.time() - (max_age_hours * 3600)
    deleted = 0
    for f in directory.iterdir():
        if f.is_file() and f.stat().st_mtime < cutoff:
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass
    if deleted:
        logger.info(f"Cleaned up {deleted} old audio files from {directory}")
    return deleted
