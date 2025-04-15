import requests

def get_api_llm(messages, API_TOKEN, API_URL, LLM_MODEL):

    # Define the headers for the API request
    headers = {
    'Authorization': f'Bearer {API_TOKEN}', 'Content-Type': 'application/json'
    }

    # Define the request payload (data)
    data = {
    "model": LLM_MODEL,
    "messages": messages
    }

    try:
        # Send the POST request to the API LLM
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"Error on: {str(e)}"}
