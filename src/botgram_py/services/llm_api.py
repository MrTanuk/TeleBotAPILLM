import logging
from typing import Any

import httpx
from httpx import HTTPStatusError, RequestError

logger = logging.getLogger(__name__)

MessageList = list[dict[str, Any]]

# CONNECTION POOLING: Reusable global client
http_client = httpx.AsyncClient(timeout=30.0)


def is_missing_env(*args: Any) -> bool:
    return any(arg is None for arg in args)


def _format_messages(
    messages: MessageList, provider: str, system_message: str | None
) -> MessageList:
    """It only handles injecting the system prompt according to the provider."""
    final_messages = list(messages)

    if not system_message:
        return final_messages

    if provider.lower() == "google":
        if final_messages and final_messages[-1]["role"] == "user":
            last_msg = final_messages[-1].copy()
            last_msg["content"] = (
                f"System Instructions: {system_message}\n\nUser Query: {last_msg['content']}"
            )
            final_messages[-1] = last_msg
        else:
            final_messages.insert(
                0, {"role": "user", "content": f"System Instructions: {system_message}"}
            )
    else:
        final_messages.insert(0, {"role": "system", "content": system_message})

    return final_messages


def _get_provider_config(
    provider: str,
    final_messages: MessageList,
    api_token: str,
    llm_model: str,
    max_tokens: int,
) -> dict[str, Any]:
    """It only handles building the JSON for the API."""
    configs: dict[str, dict[str, Any]] = {
        "openai": {
            "headers": {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            "data": {
                "model": llm_model,
                "messages": final_messages,
                "max_tokens": max_tokens,
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
                    for msg in final_messages
                ],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.9,
                    "topP": 1,
                },
            },
        },
        "deepseek": {
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {api_token}",
            },
            "data": {
                "messages": final_messages,
                "model": llm_model,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "stream": False,
            },
        },
        "groq": {
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_token}",
            },
            "data": {
                "model": llm_model,
                "messages": final_messages,
                "temperature": 0.5,
                "stream": False,
                "max_completion_tokens": max_tokens,
                "reasoning_effort": "medium",
            },
        },
    }

    if provider.lower() not in configs:
        raise KeyError(f"❌ Unsupported provider: {provider}")

    return configs[provider.lower()]


def parse_response(response: dict[str, Any], provider: str) -> str:
    """It only handles extracting the useful text from the JSON response."""
    provider = provider.lower()
    try:
        if provider in ("openai", "deepseek", "groq"):
            content = response["choices"][0]["message"].get("content")
            if content and content.strip():
                return content
        elif provider == "google":
            return response["candidates"][0]["content"]["parts"][0]["text"]

        raise KeyError(f"Unrecognized structure for provider: {provider}")

    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"Error parsing: {e}. Response: {response}")
        error_data = response.get("error")
        error_msg = (
            error_data.get("message", "Unknown error")
            if isinstance(error_data, dict)
            else str(error_data) or "Invalid JSON structure"
        )
        raise RuntimeError(f"API Error: {error_msg}")


async def get_api_llm(
    messages: MessageList,
    API_TOKEN: str,
    API_URL: str,
    LLM_MODEL: str,
    PROVIDER: str,
    MAX_OUTPUT_TOKENS: int = 1024,
    system_message: str | None = None,
) -> str:
    """Main function (Orchestrator). Now it is super clean and easy to read."""
    if is_missing_env(API_TOKEN, API_URL, LLM_MODEL, PROVIDER):
        raise ValueError("Missing some value of a key in .env. Please check it.")

    # 1. Format
    final_messages = _format_messages(messages, PROVIDER, system_message)

    # 2. Configure
    config_req = _get_provider_config(
        PROVIDER, final_messages, API_TOKEN, LLM_MODEL, MAX_OUTPUT_TOKENS
    )

    # 3. Execute petition
    try:
        response = await http_client.post(
            API_URL, json=config_req["data"], headers=config_req["headers"]
        )
        response.raise_for_status()
        return parse_response(response.json(), PROVIDER)

    except HTTPStatusError as e:
        status_code = e.response.status_code
        error_message = {
            401: "❌ Authentication failed: Invalid API token",
            429: "❌ Rate limit exceeded",
        }.get(
            status_code,
            (
                "❌ Service temporarily unavailable."
                if status_code >= 500
                else f"API request failed ({status_code})"
            ),
        )

        logger.error("API Error %s: %s", status_code, e.response.text)
        raise ConnectionError(error_message) from e

    except RequestError as e:
        logger.error("Connection error on API LLM %s", str(e))
        raise ConnectionError("❌ Network connection failed") from e
