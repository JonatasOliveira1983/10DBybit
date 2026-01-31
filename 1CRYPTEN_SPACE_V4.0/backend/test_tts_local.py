
import asyncio
import edge_tts
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TTSTest")

async def test_tts():
    text = "Teste de voz do Capitão. Câmbio."
    voice = "pt-BR-AntonioNeural"
    
    print(f"Testing TTS with Voice: {voice}")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                print(f"Received audio chunk: {len(chunk['data'])} bytes")
                break # Success
        print("TTS Generation Successful ✅")
    except Exception as e:
        print(f"TTS Failed ❌: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
