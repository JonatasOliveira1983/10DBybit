import requests
import json

def debug_info():
    url = "https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1"
    response = requests.get(url)
    data = response.json()
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    debug_info()
