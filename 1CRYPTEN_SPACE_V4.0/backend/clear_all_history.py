import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
import os
import logging
import sys
import io

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClearHistory")

async def delete_collection(db, collection_name, batch_size=500):
    """Deletes all documents in a collection in batches."""
    collection_ref = db.collection(collection_name)
    docs = collection_ref.limit(batch_size).stream()
    deleted = 0

    async def _delete_batch(batch_docs):
        batch = db.batch()
        count = 0
        for doc in batch_docs:
            batch.delete(doc.reference)
            count += 1
        await asyncio.to_thread(batch.commit)
        return count

    while True:
        # Get a batch
        current_batch_docs = [doc for doc in docs]
        if not current_batch_docs:
            break
        
        count = await _delete_batch(current_batch_docs)
        deleted += count
        logger.info(f"  Deleted {count} docs from {collection_name} (Total: {deleted})")
        
        # Get next batch
        docs = collection_ref.limit(batch_size).stream()

    return deleted

async def main():
    print("=" * 50)
    print("LIMPANDO HISTÓRICO COMPLETO (FIRESTORE)")
    print("=" * 50)
    
    cred_path = "serviceAccountKey.json"
    if not os.path.exists(cred_path):
        # Try parent dir if running from subfolder
        cred_path = os.path.join("..", "serviceAccountKey.json")
        if not os.path.exists(cred_path):
            print("ERROR: serviceAccountKey.json not found")
            return
    
    cred = credentials.Certificate(cred_path)
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    collections_to_clear = [
        "trade_history",
        "banca_history",
        "journey_signals",
        "system_logs",
        "chat_history" # Realtime DB might handle this differently, but let's check
    ]
    
    for coll in collections_to_clear:
        print(f"\nLimpando coleção: {coll}...")
        try:
            total = await delete_collection(db, coll)
            print(f"  Sucesso: {total} documentos removidos.")
        except Exception as e:
            print(f"  Erro ao limpar {coll}: {e}")

    print("\n" + "=" * 50)
    print("HISTÓRICO LIMPO COM SUCESSO")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
