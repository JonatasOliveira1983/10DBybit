import asyncio
import httpx
from supabase import create_client
from pybit.unified_trading import HTTP
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    print(f"Testing Supabase: {url}")
    try:
        client = create_client(url, key)
        # We need to use a sync call as supabase-py is sync-based for now or uses httpx internally
        # Let's try a simple select
        res = client.table("banca_status").select("*").execute()
        print("Supabase Success!")
    except Exception as e:
        print(f"Supabase Failed: {e}")

async def test_bybit():
    print("Testing Bybit...")
    try:
        session = HTTP(testnet=True)
        res = session.get_server_time()
        print(f"Bybit Success: {res}")
    except Exception as e:
        print(f"Bybit Failed: {e}")

async def main():
    await test_supabase()
    await test_bybit()

if __name__ == "__main__":
    asyncio.run(main())
