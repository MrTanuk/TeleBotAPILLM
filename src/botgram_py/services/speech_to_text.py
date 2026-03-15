import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = "whisper-large-v3-turbo"

# CONNECTION POOLING: Reusable global client
http_client = httpx.AsyncClient(timeout=30.0)


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

        if response.status_code != 200:
            logger.error(f"Groq Audio Error {response.status_code}: {response.text}")
            raise ConnectionError(f"Groq API error: {response.text}")

        result: dict[str, Any] = response.json()
        return result.get("text", "")

    except httpx.RequestError as e:
        logger.error(f"Connection error with Groq: {e}")
        raise ConnectionError("Connection failure with the transcription service.")
    except Exception as e:
        logger.error(f"Unexpected error while transcribing: {e}", exc_info=True)
        raise e
