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
                if content:
                    return content
                return message.get("reasoning_content", "Model is thinking...")
        
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


async def get_api_llm(messages, API_TOKEN, API_URL, LLM_MODEL, PROVIDER, MAX_OUTPUT_TOKENS=800):
    """
    Sends an asynchronous request to the LLM API provider and retrieves the response.

    Args:
        messages (list): List of message dicts (role, content).
        API_TOKEN (str): The API Key.
        API_URL (str): The endpoint URL.
        LLM_MODEL (str): The model name.
        PROVIDER (str): 'google', 'openai', or 'deepseek'.
        MAX_OUTPUT_TOKENS (int): Max tokens for the response.

    Returns:
        str: The generated text from the AI.
    """
    if is_missing_env(API_TOKEN, API_URL, LLM_MODEL, PROVIDER):
        raise ValueError("Missing some value of a key in .env. Please check it.")

    # Provider configuration
    provider_config = {
        "openai": {
            "headers": {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"},
            "data": {
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": int(MAX_OUTPUT_TOKENS),
            },
        },
        "google": {
            "headers": {"Content-Type": "application/json"},
            "data": {
                "contents": [
                    {
                        "role": "user" if msg["role"] in ["system", "user"] else "model",
                        "parts": [{"text": msg["content"]}],
                    }
                    for msg in messages
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
                "messages": messages,
                "model": LLM_MODEL,
                "max_tokens": int(MAX_OUTPUT_TOKENS),
                "temperature": 0.7,
                "stream": False,
            },
        },
        "groq": {
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_TOKEN}"
            },
            "data": {
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": 1,
                "stream": False,
                "max_completion_tokens": int(MAX_OUTPUT_TOKENS),
                "reasoning_effort": "medium"
            },
        },
    }

    try:
        config_req = provider_config[PROVIDER.lower()]
    except KeyError:
        raise KeyError(f"❌ Unsupported provider: {PROVIDER}")

    # Use AsyncClient for non-blocking requests. High timeout (30s) as LLMs can be slow.
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # await: Non-blocking magic happens here
            response = await client.post(
                API_URL, json=config_req["data"], headers=config_req["headers"]
            )
            response.raise_for_status()  # Raises error if status is not 200 OK

            return parse_response(response.json(), PROVIDER)

        except HTTPStatusError as e:
            # Handle HTTP errors (404, 500, 401)
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
            # Handle Network errors (DNS, Timeout, No Internet)
            logger.error("Connection error on API LLM %s", str(e))
            raise ConnectionError("❌ Network connection failed") from e
