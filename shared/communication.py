import requests
import time

def send_message(url, payload, retries=3):
    """
    Send a message to a given URL with retry logic.
    """
    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.RequestException:
            time.sleep(1)  # Retry delay
    return {"error": "Failed to send message after retries."}

def format_message(sender, content):
    """
    Format a message with metadata for consistency.
    """
    return {
        "sender": sender,
        "content": content,
        "timestamp": time.time()
    }
