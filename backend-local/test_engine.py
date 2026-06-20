import urllib.request
import json
import time

print("Waiting 3 seconds for engine check...")
time.sleep(3)

try:
    response = urllib.request.urlopen("http://127.0.0.1:7860/health", timeout=5)
    data = json.loads(response.read().decode())
    print("Health check response:")
    print(json.dumps(data, indent=2))
except Exception as e:
    print("Health check failed:", e)
