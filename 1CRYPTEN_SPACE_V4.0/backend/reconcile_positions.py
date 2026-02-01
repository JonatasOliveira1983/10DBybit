
import asyncio
from services.bybit_rest import bybit_rest_service
from firebase_admin import credentials, firestore, initialize_app, _apps

async def reconcile():
    print("🔄 RECONCILIATION: Bybit vs Firestore")
    
    # 1. Fetch Bybit Positions
    print("📡 Fetching Bybit Positions...")
    positions = await bybit_rest_service.get_positions()
    active_symbols = [p['symbol'] for p in positions if float(p['size']) > 0]
    print(f"✅ Bybit Active Positions ({len(active_symbols)}): {active_symbols}")
    
    # 2. Fetch Firestore Slots
    if not _apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        initialize_app(cred)
    db = firestore.client()
    
    print("🔥 Fetching Firestore Slots...")
    docs = db.collection("slots").stream()
    db_symbols = []
    for doc in docs:
        d = doc.to_dict()
        if d.get('symbol'):
            db_symbols.append(d['symbol'])
            
    print(f"✅ Firestore Active Slots ({len(db_symbols)}): {db_symbols}")
    
    # 3. Compare
    print("\n🧐 ANALYSIS:")
    
    # Missing in DB (Orphaned/Ghost in Exchange)
    orphans = set(active_symbols) - set(db_symbols)
    if orphans:
        print(f"⚠️  CRITICAL: Positions on Exchange but NOT in DB (Unmanaged): {orphans}")
    else:
        print("✅ No unmanaged positions on Exchange.")
        
    # Missing in Exchange (Ghost in App)
    ghosts = set(db_symbols) - set(active_symbols)
    if ghosts:
        print(f"👻 GHOSTS: Slots in DB but NOT on Exchange (Should be cleared): {ghosts}")
    else:
        print("✅ No ghost slots in DB.")

if __name__ == "__main__":
    asyncio.run(reconcile())
