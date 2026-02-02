import logging
import httpx
from httpx import RequestError, HTTPStatusError

logger = logging.getLogger(__name__)


def is_missing_env(*args):
    """Checks if any required environment variable is missing."""
    return any(arg is None for arg in args)


def parse_response(response: dict, provider: str) -> str:
    provider = provider.lower()
    try:
        if provider in ("openai", "deepseek", "groq"):
            if "choices" in response:
                message = response["choices"][0]["message"]
                content = message.get("content")
                if content and content.strip():
                    return content

        elif provider == "google":
            return response["candidates"][0]["content"]["parts"][0]["text"]

        raise KeyError(f"Estructura no reconocida para el proveedor: {provider}")

    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error parseando: {e}. Respuesta: {response}")
        error_data = response.get("error")
        if isinstance(error_data, dict):
            error_msg = error_data.get("message", "Error desconocido")
        else:
            error_msg = str(error_data) if error_data else "Estructura de JSON inválida"
        raise RuntimeError(f"API Error: {error_msg}")


async def get_api_llm(
    messages,
    API_TOKEN,
    API_URL,
    LLM_MODEL,
    PROVIDER,
    MAX_OUTPUT_TOKENS=1024,
    system_message=None,
):
    """
    Sends an asynchronous request to the LLM API provider and retrieves the response.
    Now supports dynamic system message injection.
    """
    if is_missing_env(API_TOKEN, API_URL, LLM_MODEL, PROVIDER):
        raise ValueError("Missing some value of a key in .env. Please check it.")

    final_messages = list(messages)

    if system_message:
        if PROVIDER.lower() == "google":
            if final_messages and final_messages[-1]["role"] == "user":
                last_msg = final_messages[-1].copy()
                last_msg["content"] = (
                    f"System Instructions: {system_message}\n\nUser Query: {last_msg['content']}"
                )
                final_messages[-1] = last_msg
            else:
                final_messages.insert(
                    0,
                    {
                        "role": "user",
                        "content": f"System Instructions: {system_message}",
                    },
                )

        else:
            final_messages.insert(0, {"role": "system", "content": system_message})

    # ----------------------------------------

    # Provider configuration
    provider_config = {
        "openai": {
            "headers": {
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json",
            },
            "data": {
                "model": LLM_MODEL,
                "messages": final_messages,  # Use the modified list
                "max_tokens": int(MAX_OUTPUT_TOKENS),
            },
        },
        "google": {
            "headers": {"Content-Type": "application/json"},
            "data": {
                "contents": [
                    {
                        "role": (
                            "user" if msg["role"] in ["system", "user"] else "model"
                        ),
                        "parts": [{"text": msg["content"]}],
                    }
                    for msg in final_messages  # Use the modified list
                ],
                "generationConfig": {
                    "maxOutputTokens": int(MAX_OUTPUT_TOKENS),
                    "temperature": 0.9,
                    "topP": 1,
                },
            },
        },
        "deepseek": {
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {API_TOKEN}",
            },
            "data": {
                "messages": final_messages,
                "model": LLM_MODEL,
                "max_tokens": int(MAX_OUTPUT_TOKENS),
                "temperature": 0.7,
                "stream": False,
            },
        },
        "groq": {
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_TOKEN}",
            },
            "data": {
                "model": LLM_MODEL,
                "messages": final_messages,
                "temperature": 0.5,
                "stream": False,
                "max_completion_tokens": int(MAX_OUTPUT_TOKENS),
                "reasoning_effort": "medium",
            },
        },
    }

    try:
        config_req = provider_config[PROVIDER.lower()]
    except KeyError:
        raise KeyError(f"❌ Unsupported provider: {PROVIDER}")

    # Use AsyncClient for non-blocking requests.
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                API_URL, json=config_req["data"], headers=config_req["headers"]
            )
            response.raise_for_status()

            return parse_response(response.json(), PROVIDER)

        except HTTPStatusError as e:
            status_code = e.response.status_code
            error_message = f"API request failed (status {status_code})"

            if status_code == 401:
                error_message = "❌ Authentication failed: Invalid API token"
            elif status_code == 429:
                error_message = "❌ Rate limit exceeded"
            elif status_code >= 500:
                error_message = "❌ Service temporarily unavailable."

            logger.error("API Error %s: %s", status_code, e.response.text)
            raise ConnectionError(error_message) from e

        except RequestError as e:
            logger.error("Connection error on API LLM %s", str(e))
            raise ConnectionError("❌ Network connection failed") from e
