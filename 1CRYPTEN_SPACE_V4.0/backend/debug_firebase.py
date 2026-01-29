
import firebase_admin
from firebase_admin import credentials, db
import os
import json

KEY_PATH = "serviceAccountKey.json"
ENV_URL = "https://projeto-teste-firestore-3b00e-default-rtdb.firebaseio.com"
LEGACY_URL = "https://projeto-teste-firestore-3b00e.firebaseio.com"

def test_connection(url):
    print(f"\n--- Testing URL: {url} ---")
    try:
        cred = credentials.Certificate(KEY_PATH)
        # Unique app name to allow multiple inits
        app_name = f"tester_{hash(url)}"
        try:
            app = firebase_admin.get_app(app_name)
        except ValueError:
            app = firebase_admin.initialize_app(cred, {'databaseURL': url}, name=app_name)
        
        ref = db.reference("test_connection", app=app)
        ref.set({"status": "ok", "timestamp": "now"})
        print("✅ WRITE SUCCESS!")
        return True
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")
        return False

if __name__ == "__main__":
    print("Loading credentials...")
    if not os.path.exists(KEY_PATH):
        print("Key not found!")
        exit(1)
        
    print("1. Testing Configured URL (from .env)...")
    if test_connection(ENV_URL):
        print("Configured URL is VALID.")
    else:
        print("Configured URL FAILED.")
        
        print("\n2. Testing Legacy URL...")
        if test_connection(LEGACY_URL):
            print("Legacy URL is VALID. Please update .env.")
        else:
            print("Legacy URL FAILED.")
