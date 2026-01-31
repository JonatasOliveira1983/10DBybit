
import asyncio
import edge_tts

async def list_voices():
    voices = await edge_tts.VoicesManager.create()
    pt_voices = voices.find(Locale="pt-BR")
    for v in pt_voices:
        print(f"ID: {v['Name']}, Name: {v['FriendlyName']}, Gender: {v['Gender']}")

if __name__ == "__main__":
    asyncio.run(list_voices())
