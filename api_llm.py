from sys import exc_info
import requests
import logging
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

def is_env_exist(API_TOKEN, API_URL, LLM_MODEL, PROVIDER):
    if None in (API_TOKEN, API_URL, LLM_MODEL, PROVIDER):
        return True
    return False

def parse_response(response: dict, provider: str) -> str:
    provider = provider.lower()
    if provider in ("openai", "deepseek"):
        return response['choices'][0]['message']['content']
    elif provider == "google":
        return response['candidates'][0]['content']['parts'][0]['text']
    return str(response)

def get_api_llm(messages, API_TOKEN, API_URL, LLM_MODEL, PROVIDER, MAX_OUTPUT_TOKENS=2048):
    # Provider configuration mapping
    provider_config = {
        "openai": {
            "headers": {
                'Authorization': f'Bearer {API_TOKEN}',
                'Content-Type': 'application/json'
            },
            "data": {
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": MAX_OUTPUT_TOKENS
            }
        },
        "google": {
            "headers": {
                'Content-Type': 'application/json'
            },
            "data": {
                "contents": [
                    {
                        "role": "user" if msg["role"] in ["system", "user"] else "model",
                        "parts": [{"text": msg["content"]}]
                    } 
                    for msg in messages
                ],
                "generationConfig": {
                "maxOutputTokens": MAX_OUTPUT_TOKENS,
                "temperature": 0.9,
                "topP": 1
                }
            }
        },
        "deepseek": {
            "headers": {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {API_TOKEN}'
            },
            "data": {
                "messages": messages,
                "model": LLM_MODEL,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "temperature": 0.7,
                "stream": False
            }
        }
    }
    
    if is_env_exist(API_TOKEN, API_URL, LLM_MODEL, PROVIDER):
        return "Missing some value of a key. Check it"

    try:
        config = provider_config[PROVIDER.lower()]
    except KeyError:
        raise KeyError(f"❌ Unsupported provider: {PROVIDER}")

    try:
        response = requests.post(
            API_URL,
            json=config["data"],
            headers=config["headers"],
            timeout=15,
        )
        response.raise_for_status()
        return parse_response(response.json(), PROVIDER)
        
    except RequestException as e:
        status_code = getattr(e.response, 'status_code', None)
        error_message = f"API request failed"
        
        if status_code:
            error_message += f" (status {status_code})"
            if status_code == 401:
                error_message = "❌ Authentication failed: Invalid API token"
            elif status_code == 429:
                error_message = "❌ Rate limit exceeded"
            elif status_code == 404:
                error_message = "❌ API endpoint not found"
            elif status_code >= 500:
                error_message = "❌ Service temporarily unavailable. Please try again in a few seconds."
        
        logger.error("Connection error on API LLM %s", str(e), exc_info=True)
        raise ConnectionError(error_message) from e
    except Exception as e:
        logger.error("Unexpected error on API LLM %s", str(e), exc_info=True)
        raise RuntimeError(f"🚨 Unexpected error: {str(e)}") from e
