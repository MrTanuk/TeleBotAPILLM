from sys import exception
import requests
from requests.api import request

def getApiDeepSeek(input_user, API_KEY, API_URL):

    # Define the headers for the API request
    headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
    }

    # Define the request payload (data)
    data = {
    "model": "deepseek/deepseek-chat:free",
    "messages": [{"role": "user", "content": input_user}]
    }

    try:
        # Send the POST request to the DeepSeek API
        response = requests.post(API_URL, json=data, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        return {"error": f"Error on: {str(e)}"}
