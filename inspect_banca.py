import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "1CRYPTEN_SPACE_V4.0", "backend"))

async def inspect():
    # Load credentials
    import os
    import json
    from firebase_admin import credentials
    
    cred_path = os.path.join("1CRYPTEN_SPACE_V4.0", "backend", "serviceAccountKey.json")
    if os.path.exists(cred_path):
        os.chdir(os.path.join("1CRYPTEN_SPACE_V4.0", "backend"))
        # After chdir, the script will find it in the current dir
    
    from services.firebase_service import firebase_service
    from services.bybit_rest import bybit_rest_service
    from services.bankroll import bankroll_manager
    
    await firebase_service.initialize()
    await bybit_rest_service.initialize()
    
    print("Triggering bankroll update...")
    await bankroll_manager.update_banca_status()
    
    status = await firebase_service.get_banca_status()
    print("--- UPDATED BANCA STATUS ---")
    for k, v in status.items():
        print(f"{k}: {v}")
    print("----------------------------")

if __name__ == "__main__":
    asyncio.run(inspect())
