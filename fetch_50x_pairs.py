import requests
import json

def get_50x_pairs():
    url = "https://api.bybit.com/v5/market/instruments-info"
    params = {
        "category": "linear",
        "limit": 1000
    }
    
    pairs_50x = []
    cursor = ""
    
    while True:
        if cursor:
            params["cursor"] = cursor
            
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['retCode'] != 0:
            print(f"Error: {data['retMsg']}")
            break

        instruments = data['result']['list']
        for instr in instruments:
            symbol = instr['symbol']
            if not symbol.endswith('USDT'):
                continue
                
            leverage_filter = instr.get('leverageFilter', {})
            max_leverage_str = leverage_filter.get('maxLeverage', '0')
            try:
                max_leverage = float(max_leverage_str)
            except ValueError:
                max_leverage = 0
            
            # The user wants "at most 50x and at least 50x", meaning exactly 50x max leverage.
            if max_leverage == 50.0:
                pairs_50x.append(symbol)
                
        cursor = data['result'].get('nextPageCursor')
        if not cursor:
            break
            
    pairs_50x.sort()
    return pairs_50x

if __name__ == "__main__":
    pairs = get_50x_pairs()
    if pairs:
        print(json.dumps(pairs, indent=2))
    else:
        print("No pairs found.")
