import logging
import httpx

logger = logging.getLogger(__name__)

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
MODEL = "whisper-large-v3-turbo"


async def transcribe(audio_bytes: bytes, api_key: str) -> str:
    """
    Transcribe audio using the Groq API (Whisper).
    Accepts direct bytes (Telegram OGG) and returns text.
    """
    if not api_key:
        raise ValueError("❌ No API Key was provided for Groq Audio.")

    headers = {"Authorization": f"Bearer {api_key}"}

    files = {"file": ("voice.ogg", audio_bytes, "audio/ogg")}

    data = {"model": MODEL, "temperature": "0", "response_format": "json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_WHISPER_URL, headers=headers, files=files, data=data
            )

            if response.status_code != 200:
                logger.error(
                    f"Groq Audio Error {response.status_code}: {response.text}"
                )
                raise ConnectionError(f"Groq API error: {response.text}")

            result = response.json()
            return result.get("text", "")

    except httpx.RequestError as e:
        logger.error(f"Connection error with Groq: {e}")
        raise ConnectionError("Connection failure with the transcription service.")
    except Exception as e:
        logger.error(f"Unexpected error while transcribing: {e}", exc_info=True)
        raise e
