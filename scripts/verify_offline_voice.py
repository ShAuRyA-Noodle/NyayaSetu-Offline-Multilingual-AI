#!/usr/bin/env python
"""
Verify the fully-offline voice round-trip: TTS -> WAV -> ASR -> text.

Synthesizes a phrase with offline TTS (pyttsx3, Windows SAPI / eSpeak), writes a
WAV, then transcribes it back with offline ASR (faster-whisper, int8). No cloud,
no network at inference time (the whisper model is fetched once and cached).

Proves the offline ASR/TTS lane the paper describes actually works end-to-end.

    .venv-ml/Scripts/python.exe scripts/verify_offline_voice.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def synth(phrase: str, wav_path: str) -> bool:
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.save_to_file(phrase, wav_path)
    engine.runAndWait()
    return os.path.exists(wav_path) and os.path.getsize(wav_path) > 0


def transcribe(wav_path: str, model_size: str) -> tuple[str, str, float]:
    from faster_whisper import WhisperModel

    model = None
    for attempt in range(4):
        try:
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            break
        except Exception as e:  # noqa: BLE001
            print(f"  model load retry {attempt}: {type(e).__name__}")
            time.sleep(3 * (attempt + 1))
    if model is None:
        raise RuntimeError("could not load faster-whisper model")

    t0 = time.time()
    segments, info = model.transcribe(wav_path, beam_size=5)
    text = " ".join(s.text for s in segments).strip()
    return text, info.language, time.time() - t0


def word_overlap(a: str, b: str) -> float:
    sa = {w.strip(".,!?").lower() for w in a.split()}
    sb = {w.strip(".,!?").lower() for w in b.split()}
    if not sa:
        return 0.0
    return len(sa & sb) / len(sa)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phrase", default="the farmer needs help with the pension scheme")
    p.add_argument("--model", default="tiny", choices=["tiny", "base", "small"])
    p.add_argument("--out", default="eval/results/offline_voice.json")
    args = p.parse_args()

    wav = os.path.join(tempfile.gettempdir(), "nyaya_voice_roundtrip.wav")
    print(f"TTS: synthesizing '{args.phrase}' (offline)...")
    if not synth(args.phrase, wav):
        print("TTS failed")
        return 1
    print(f"  wrote {os.path.getsize(wav)} bytes")

    print(f"ASR: transcribing with faster-whisper '{args.model}' (offline)...")
    text, lang, latency = transcribe(wav, args.model)
    overlap = word_overlap(args.phrase, text)
    print(f"  ASR -> {text!r}  (lang={lang}, {latency:.1f}s)")
    print(f"  word overlap with reference: {overlap:.0%}")

    result = {
        "reference": args.phrase,
        "asr_model": f"faster-whisper {args.model} (int8, offline)",
        "tts": "pyttsx3 (offline)",
        "transcription": text,
        "detected_language": lang,
        "asr_latency_s": round(latency, 2),
        "word_overlap": round(overlap, 3),
        "roundtrip_ok": overlap >= 0.5,
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRound-trip {'OK' if result['roundtrip_ok'] else 'WEAK'} "
          f"({overlap:.0%} word overlap). Written: {args.out}")
    return 0 if result["roundtrip_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
