
import asyncio
from services.bybit_rest import bybit_rest_service
from firebase_admin import credentials, firestore, initialize_app, _apps
import time

from config import settings
import os
from dotenv import load_dotenv

async def adopt_orphans():
    print("🛸 PROTOCOL ORPHAN ADOPTION INITIALIZED")
    
    # FORCE ENV LOAD
    env_path = os.path.join(os.getcwd(), ".env")
    load_dotenv(env_path, override=True)
    
    # Reload settings manually from env if needed or just use os.environ
    settings.BYBIT_API_KEY = os.getenv("BYBIT_API_KEY") or settings.BYBIT_API_KEY
    settings.BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET") or settings.BYBIT_API_SECRET
    
    # DEBUG KEYS
    key = settings.BYBIT_API_KEY
    print(f"🔑 API Key Loaded: {'YES (Ends with ' + key[-4:] + ')' if key else 'NO (None)'}")
    print(f"📂 Current Dir: {os.getcwd()}")
    
    # 1. Initialize DB
    if not _apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        initialize_app(cred)
    db = firestore.client()
    
    # 2. Get Real Positions
    print("📡 Scanning Bybit Sector...")
    try:
        # Use session directly to get positions (since wrapper might not exist)
        # Note: calling internal method or using a known reliable one
        # Assuming get_wallet_balance might work, but let's try raw session call
        await bybit_rest_service.initialize()
        
        # Helper to get positions via raw session
        resp = await asyncio.to_thread(
            bybit_rest_service.session.get_positions, 
            category="linear", 
            settleCoin="USDT"
        )
        pos_list = resp.get("result", {}).get("list", [])
        active_positions = [p for p in pos_list if float(p["size"]) > 0]
        
        print(f"✅ Found {len(active_positions)} active signatures on Exchange.")
        
    except Exception as e:
        print(f"❌ SCAN ERROR: {e}")
        return

    # 3. Get Managed Slots
    slots_ref = db.collection("slots")
    docs = slots_ref.stream()
    managed_symbols = {}
    occupied_ids = []
    
    for doc in docs:
        d = doc.to_dict()
        if d.get("symbol"):
            managed_symbols[d["symbol"]] = doc.id
            occupied_ids.append(d["id"])
            
    print(f"📋 Managed Slots: {list(managed_symbols.keys())}")
    
    # 4. Identify Orphans
    orphans = []
    for pos in active_positions:
        sym = pos["symbol"]
        if sym not in managed_symbols:
            orphans.append(pos)
            
    if not orphans:
        print("✅ No orphans detected. All clear.")
        return
        
    print(f"⚠️  {len(orphans)} ORPHANS DETECTED: {[o['symbol'] for o in orphans]}")
    
    # 5. Adopt Them
    available_ids = [i for i in range(1, 11) if i not in occupied_ids]
    
    for orphan in orphans:
        if not available_ids:
            print("❌ No empty slots available for adoption!")
            break
            
        slot_id = available_ids.pop(0)
        sym = orphan["symbol"]
        side = orphan["side"]
        entry = float(orphan["avgPrice"])
        size = float(orphan["size"])
        
        print(f"🚑 Adopting {sym} into Slot {slot_id}...")
        
        # Create Slot Data
        # Default to SNIPER logic for safety, unless specified otherwise
        slot_data = {
            "id": slot_id,
            "symbol": sym,
            "side": side,
            "size": size,
            "entry_price": entry,
            "current_stop": float(orphan.get("stopLoss", 0)) if float(orphan.get("stopLoss", 0)) > 0 else entry * (0.5 if side == "Buy" else 1.5), # Emergency SL
            "pnl_percent": 0.0, # Will update next tick
            "status": "ADOPTED",
            "slot_type": "SNIPER" if slot_id <= 5 else "SURF",
            "timestamp": int(time.time() * 1000)
        }
        
        slots_ref.document(str(slot_id)).set(slot_data)
        print(f"✨ {sym} adopted successfully into Slot {slot_id}.")

    print("🏁 Adoption Protocol Complete.")

if __name__ == "__main__":
    asyncio.run(adopt_orphans())
