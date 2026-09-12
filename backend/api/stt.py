"""Local Speech-to-Text endpoint using Whisper.

Fallback STT for when the browser's Web Speech API cannot reach Google's
speech servers (firewall, no internet, non-https origin).

    POST /api/stt
    Content-Type: multipart/form-data
    Body: audio=<file>, lang=<optional language code>
    Response: { "transcript": "..." }
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException

LOG = logging.getLogger(__name__)

router = APIRouter()

# Lazy-loaded Whisper model (singleton)
_whisper_model = None
_whisper_available: bool | None = None


def _get_whisper_model():
    """Load faster-whisper model on first use."""
    global _whisper_model, _whisper_available
    if _whisper_available is False:
        return None
    if _whisper_model is not None:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel
        # Use 'base' for speed; 'small' or 'medium' for better accuracy
        model_size = "base"
        LOG.info("Loading faster-whisper model '%s'...", model_size)
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        _whisper_available = True
        LOG.info("faster-whisper model loaded successfully.")
        return _whisper_model
    except ImportError:
        LOG.warning(
            "faster-whisper not installed. Install with: pip install faster-whisper\n"
            "Local STT will not be available."
        )
        _whisper_available = False
        return None
    except Exception as exc:
        LOG.error("Failed to load Whisper model: %s", exc)
        _whisper_available = False
        return None


@router.post("/api/stt")
async def speech_to_text(request: Request):
    """Transcribe uploaded audio using local Whisper model or raw bytes fallback."""
    # Check multipart support dynamically
    content_type = request.headers.get("content-type", "")
    audio_bytes: bytes = b""
    filename = "audio.webm"
    lang = "en"

    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
            audio_field = form.get("audio")
            if audio_field is not None and hasattr(audio_field, "read"):
                audio_bytes = await audio_field.read()
                filename = getattr(audio_field, "filename", "audio.webm") or "audio.webm"
            lang = str(form.get("lang") or "en")
        except Exception as exc:
            LOG.warning("Failed parsing multipart form in /api/stt: %s", exc)
            raise HTTPException(
                status_code=400,
                detail="Failed to parse multipart audio form. Ensure python-multipart is installed.",
            )
    else:
        # Accept raw audio stream in request body as well
        audio_bytes = await request.body()
        lang = request.query_params.get("lang", "en")

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data provided.")

    model = _get_whisper_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Local speech-to-text is not available. "
                "Install faster-whisper: pip install faster-whisper"
            ),
        )

    # Save uploaded audio to temp file
    suffix = Path(filename).suffix or ".webm"
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Transcribe
        segments, info = model.transcribe(
            tmp_path,
            language=lang[:2] if lang else "en",  # faster-whisper uses 2-letter codes
            beam_size=5,
            vad_filter=True,
        )

        transcript = " ".join(seg.text.strip() for seg in segments)
        LOG.info("STT result (lang=%s, dur=%.1fs): %s", info.language, info.duration, transcript[:100])

        return {"transcript": transcript, "language": info.language, "duration": info.duration}

    except Exception as exc:
        LOG.error("STT transcription failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")
    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
