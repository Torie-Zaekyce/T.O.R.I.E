import asyncio
import io
import os
import tempfile
import uuid

import edge_tts

DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_RATE  = "+0%"
DEFAULT_PITCH = "+0Hz"

_MAX_TTS_CHARS = 600


async def generate_tts(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
) -> str | None:
    """
    Generate speech audio from text and save it to a temp .mp3 file.

    Returns the file path on success, or None on failure.
    Caller is responsible for deleting the file after use (see cleanup_tts_file).
    """
    text = text.strip()
    if not text:
        return None
    if len(text) > _MAX_TTS_CHARS:
        text = text[:_MAX_TTS_CHARS].rsplit(" ", 1)[0] + "…"

    out_path = os.path.join(tempfile.gettempdir(), f"torie_tts_{uuid.uuid4().hex}.mp3")

    try:
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(out_path)
        return out_path
    except Exception as e:
        print(f"⚠️ TTS generation failed: {type(e).__name__}: {e}")
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
        return None


async def generate_tts_bytes(
    text: str,
    voice: str = DEFAULT_VOICE,
    rate: str = DEFAULT_RATE,
    pitch: str = DEFAULT_PITCH,
) -> bytes | None:
    """
    Same as generate_tts, but returns raw mp3 bytes in memory instead of
    writing to disk. Useful for piping directly into other audio tools
    (e.g. the VTube Studio lip-sync pipeline) without touching the filesystem.
    """
    text = text.strip()
    if not text:
        return None
    if len(text) > _MAX_TTS_CHARS:
        text = text[:_MAX_TTS_CHARS].rsplit(" ", 1)[0] + "…"

    try:
        buffer = io.BytesIO()
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        return buffer.getvalue()
    except Exception as e:
        print(f"⚠️ TTS generation (bytes) failed: {type(e).__name__}: {e}")
        return None


def cleanup_tts_file(path: str) -> None:
    """Delete a temp TTS file. Safe to call even if the file is already gone."""
    if not path:
        return
    try:
        os.remove(path)
    except OSError:
        pass


async def list_voices(locale_filter: str | None = None) -> list[dict]:
    """
    List available edge-tts voices, optionally filtered by locale prefix
    (e.g. "en-US", "en-GB"). Returns a list of voice metadata dicts.
    """
    voices = await edge_tts.list_voices()
    if locale_filter:
        voices = [v for v in voices if v["Locale"].lower().startswith(locale_filter.lower())]
    return voices
