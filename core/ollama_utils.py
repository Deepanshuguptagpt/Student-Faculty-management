import requests
import json

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "tinyllama:latest" # Using a lighter model to fit in available system memory

def generate_ollama_insight(prompt):
    """
    Calls local Ollama API to generate a summary or insight.
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=90)
        if response.status_code == 200:
            return response.json().get('response', "No insight generated.")
        else:
            return f"Ollama Error: Status {response.status_code}"
    except Exception as e:
        return f"Ollama Connection Failed: {str(e)}"
