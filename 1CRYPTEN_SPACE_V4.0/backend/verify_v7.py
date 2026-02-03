import urllib.request
import json
import os

def verify():
    results = {}
    try:
        results['status'] = json.loads(urllib.request.urlopen('http://127.0.0.1:8081/api/vault/status').read().decode())
        results['history'] = json.loads(urllib.request.urlopen('http://127.0.0.1:8081/api/vault/history').read().decode())
        
        with open('verification_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("Verification complete.")
    except Exception as e:
        with open('verification_error.txt', 'w') as f:
            f.write(str(e))
        print(f"Verification failed: {e}")

if __name__ == "__main__":
    verify()
