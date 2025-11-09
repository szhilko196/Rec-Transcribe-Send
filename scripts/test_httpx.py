"""Test using httpx instead of requests"""
import httpx

url = "http://127.0.0.1:8002/health"

print(f"Testing with httpx: {url}")

try:
    response = httpx.get(url, timeout=5.0)
    print(f"Status code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Content: {response.text}")
    print(f"JSON: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
