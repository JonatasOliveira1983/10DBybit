import asyncio
import sys
import os

# Add backend to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.agents.ai_service import ai_service

async def test_glm():
    print("Testing GLM-4.7 Connectivity...")
    prompt = "Responda apenas com 'OK' se você estiver funcionando."
    response = await ai_service.generate_content(prompt)
    if response:
        print(f"GLM/Gemini Response: {response}")
    else:
        print("Failed to get any AI response.")

if __name__ == "__main__":
    asyncio.run(test_glm())
