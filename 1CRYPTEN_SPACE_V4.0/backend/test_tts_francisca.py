
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
    text = "Teste de voz da Francisca."
    voice = "pt-BR-FranciscaNeural"
    
    print(f"Testing TTS with Voice: {voice}")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save("test_audio_francisca.mp3")
        print("TTS Generation Successful: output saved to test_audio_francisca.mp3 ✅")
    except Exception as e:
        print(f"TTS Failed ❌: {e}")

if __name__ == "__main__":
    asyncio.run(test_tts())
