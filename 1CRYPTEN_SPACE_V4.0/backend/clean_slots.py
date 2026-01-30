# -*- coding: utf-8 -*-
"""
Clean Slots V4.5.1 - Protocol Elite Reset
============================================
Limpa todos os slots e paper positions para testes do novo protocolo.

Author: Antigravity AI
Usage: python clean_slots.py
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import firebase_admin
from firebase_admin import credentials, firestore

print("=" * 60)
print("Protocol Elite V4.5.1 - SYSTEM RESET")
print("=" * 60)

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass  # Already initialized

db = firestore.client()

def clean_all():
    # 1. Reset all 10 slots to clean state
    print("\n[RESET] Resetting slots_ativos to clean state...")
    slots_ref = db.collection('slots_ativos')
    
    for i in range(1, 11):
        slot_id = str(i)
        slot_type = "SNIPER" if i <= 5 else "SURF"
        
        clean_slot = {
            "id": i,
            "symbol": None,
            "side": None,
            "entry_price": 0,
            "current_stop": 0,
            "target_price": None,
            "status_risco": "LIVRE",
            "pnl_percent": 0,
            "slot_type": slot_type,
            "visual_status": "SCANNING",
            "current_price": 0,
            "pensamento": "Reset para Protocol Elite V4.5.1"
        }
        
        slots_ref.document(slot_id).set(clean_slot)
        print(f"   [OK] Slot {i} ({slot_type}) -> RESET")
    
    print(f"\n[SUCCESS] All 10 slots reset successfully!")
    
    # 2. Show summary
    print("\n" + "=" * 60)
    print("SLOTS CONFIGURATION V4.5.1:")
    print("   Slots 1-5: SNIPER (Flash Close, 100% ROI target)")
    print("   Slots 6-10: SURF (Trailing Stop, Risco Zero)")
    print("=" * 60)
    
    # 3. Clear paper positions note
    print("\n[NOTE] Para limpar paper positions do backend,")
    print("       reinicie o servidor (main.py)")
    print("\n[READY] Sistema pronto para novos testes!")

if __name__ == "__main__":
    clean_all()
