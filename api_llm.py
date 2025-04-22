import requests

def parse_response(response, provider):
    # Analize the anwser according the provider
    if provider == "openai" or provider == "deepseek":
        return response['choices'][0]['message']['content']
    elif provider == "google":
        return response['candidates'][0]['content']['parts'][0]['text']
    else:
        return response

def get_api_llm(messages, API_TOKEN, API_URL, LLM_MODEL, MAX_OUTPUT_TOKENS=2048, provider="google"):
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

    try:
        config = provider_config[provider.lower()]
    except KeyError:
        return {"error": f"Unsupported provider: {provider}"}

    try:
        response = requests.post(
            API_URL,
            json=config["data"],
            headers=config["headers"]
        )
        response.raise_for_status()
        return parse_response(response.json(), provider)
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
