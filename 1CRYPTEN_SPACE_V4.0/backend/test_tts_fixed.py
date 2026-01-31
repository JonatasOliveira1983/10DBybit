
import asyncio
import edge_tts
import logging
import sys

# Windows Proactor Event Loop Fix
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TTSTest")

async def test_tts():
    text = "Teste de voz do Capitão."
    voice = "pt-BR-AntonioNeural"
    
    print(f"Testing TTS with Voice: {voice}")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        # Using the file output method to be simpler and avoid stream complexities
        await communicate.save("test_audio.mp3")
        print("TTS Generation Successful: output saved to test_audio.mp3 ✅")
    except Exception as e:
        print(f"TTS Failed ❌: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
