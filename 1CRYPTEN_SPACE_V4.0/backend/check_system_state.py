import firebase_admin
from firebase_admin import credentials, firestore, db
import os
import json
from datetime import datetime

def main():
    cred_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://projeto-teste-firestore-3b00e-default-rtdb.europe-west1.firebasedatabase.app'
        })
    
    fs_client = firestore.client()
    
    print("\n--- Firestore: vault_management/current_cycle ---")
    cycle = fs_client.collection("vault_management").document("current_cycle").get().to_dict()
    print(json.dumps(cycle, indent=2, default=str))
    
    print("\n--- Firestore: slots_ativos ---")
    try:
        # Set a timeout for the stream/get operations if possible, seeing hangs
        # Firestore client doesn't support simple timeout arg easily, so we use a thread hack or just print before/after
        print("[DEBUG] Fetching slots from Firestore...")
        slots = list(fs_client.collection("slots_ativos").stream())
        slots_data = [s.to_dict() for s in slots]
        print(json.dumps(slots_data, indent=2, default=str))
    except Exception as e:
        print(f"[ERROR] Firestore Slots: {e}")

    # Add RTDB Pulse Check
    print("\n--- RTDB: system_pulse ---")
    try:
        print("[DEBUG] Connecting to RTDB...")
        # Force a timeout explicitly via socket default if needed, or just relying on print debugging
        import socket
        socket.setdefaulttimeout(10) # 10s timeout
        
        ref = db.reference("system_pulse")
        print("[DEBUG] Fetching Pulse...")
        pulse = ref.get()
        print(json.dumps(pulse, indent=2, default=str))
        
        if pulse and 'timestamp' in pulse:
            diff = (datetime.now().timestamp() * 1000) - pulse['timestamp']
            print(f"Pulse Latency: {diff/1000:.2f}s")
    except Exception as e:
        print(f"RTDB Error: {e}")

if __name__ == "__main__":
    main()
