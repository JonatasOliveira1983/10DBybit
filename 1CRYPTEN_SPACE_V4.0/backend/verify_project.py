import os
import firebase_admin
from firebase_admin import credentials
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verifier")

def check():
    # 1. Check Env
    cred_json = os.getenv("FIREBASE_CREDENTIALS")
    if cred_json:
        print("FIREBASE_CREDENTIALS ENV found.")
        data = json.loads(cred_json)
        print(f"Project ID in ENV: {data.get('project_id')}")
    else:
        print("No FIREBASE_CREDENTIALS ENV found.")
        
    # 2. Check local file
    cred_path = "serviceAccountKey.json"
    if os.path.exists(cred_path):
        with open(cred_path) as f:
            data = json.load(f)
            print(f"Project ID in local file: {data.get('project_id')}")
            
    # 3. Check initialized app
    try:
        from services.firebase_service import firebase_service
        import asyncio
        async def init():
            await firebase_service.initialize()
            app = firebase_admin.get_app()
            print(f"Current Running Project ID: {app.project_id}")
            
            # Check slots count
            slots = await firebase_service.get_active_slots()
            active = [s for s in slots if s.get('symbol')]
            print(f"Active Slots Found: {len(active)}")
            for s in active:
                print(f" - {s.get('symbol')} (ROI: {s.get('pnl_percent')}%)")
                
        asyncio.run(init())
    except Exception as e:
        print(f"Error checking running app: {e}")

if __name__ == "__main__":
    check()
