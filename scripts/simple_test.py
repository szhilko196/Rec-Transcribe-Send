"""Simple test for debugging"""
import requests

url = "http://127.0.0.1:8002/health"

print(f"Testing: {url}")

try:
    response = requests.get(url, timeout=5)
    print(f"Status code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Content: {response.text}")
    print(f"JSON: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
