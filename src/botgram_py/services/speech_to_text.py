import logging
from typing import Any

import httpx
from httpx import HTTPStatusError, RequestError

logger = logging.getLogger(__name__)

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = "whisper-large-v3-turbo"

# CONNECTION POOLING: Reusable global client with explicit limits
http_client = httpx.AsyncClient(
    timeout=60.0,
    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
)


async def transcribe(audio_bytes: bytes, api_key: str) -> str:
    if not api_key:
        raise ValueError("❌ No API Key was provided for Groq Audio.")

    headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"}
    files: dict[str, tuple[str, bytes, str]] = {
        "file": ("voice.ogg", audio_bytes, "audio/ogg")
    }
    data: dict[str, str] = {
        "model": MODEL,
        "temperature": "0",
        "response_format": "json",
    }

    try:
        response = await http_client.post(
            GROQ_WHISPER_URL, headers=headers, files=files, data=data
        )
        response.raise_for_status()

        result: dict[str, Any] = response.json()
        return result.get("text", "")

    except HTTPStatusError as e:
        logger.error("Groq Audio Error %s: %s", e.response.status_code, e.response.text)
        raise ConnectionError(f"Groq API error ({e.response.status_code})") from e
    except RequestError as e:
        logger.error("Connection error with Groq: %s", e)
        raise ConnectionError("Connection failure with the transcription service.") from e
