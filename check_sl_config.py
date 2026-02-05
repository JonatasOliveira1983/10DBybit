
def calculate_sl_tp(entry_price, leverage=50):
    sl_percent = 0.01  # 1%
    tp_percent = 0.02  # 2%
    
    # Buy Side
    sl_buy = entry_price * (1 - sl_percent)
    tp_buy = entry_price * (1 + tp_percent)
    
    # Sell Side
    sl_sell = entry_price * (1 + sl_percent)
    tp_sell = entry_price * (1 - tp_percent)
    
    print(f"Entry Price: {entry_price}")
    print(f"Leverage: {leverage}x")
    print("-" * 20)
    print(f"BUY SL (1% dist): {sl_buy:.2f} | Decrease: {entry_price - sl_buy:.2f} ({((entry_price - sl_buy)/entry_price)*100:.1f}%)")
    print(f"BUY TP (2% dist): {tp_buy:.2f} | Increase: {tp_buy - entry_price:.2f} ({((tp_buy - entry_price)/entry_price)*100:.1f}%)")
    print("-" * 20)
    print(f"SELL SL (1% dist): {sl_sell:.2f} | Increase: {sl_sell - entry_price:.2f} ({((sl_sell - entry_price)/entry_price)*100:.1f}%)")
    print(f"SELL TP (2% dist): {tp_sell:.2f} | Decrease: {entry_price - tp_sell:.2f} ({((entry_price - tp_sell)/entry_price)*100:.1f}%)")
    print("-" * 20)
    
    # ROI Verification
    roi_sl_buy = ((sl_buy - entry_price) / entry_price) * leverage * 100
    roi_tp_buy = ((tp_buy - entry_price) / entry_price) * leverage * 100
    
    print(f"ROI at SL (Buy): {roi_sl_buy:.1f}%")
    print(f"ROI at TP (Buy): {roi_tp_buy:.1f}%")

if __name__ == "__main__":
    calculate_sl_tp(50000)
