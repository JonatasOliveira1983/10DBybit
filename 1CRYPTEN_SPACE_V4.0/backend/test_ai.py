import asyncio
import logging
import sys
import os

# Set up paths to import services
sys.path.append(os.getcwd())

from services.agents.ai_service import ai_service

async def test_ai():
    logging.basicConfig(level=logging.INFO)
    print("--- 1CRYPTEN AI DIAGNOSTIC ---")
    
    prompt = "Olá Oráculo, você está online? Quem é você?"
    instruction = "Você é o Oráculo Soberano da 1CRYPTEN. Um mentor de elite."
    
    print(f"Enviando prompt: '{prompt}'")
    print("Aguardando resposta...")
    
    try:
        response = await ai_service.generate_content(prompt, system_instruction=instruction)
        print("\n--- RESPOSTA RECEBIDA ---")
        print(response)
        print("--------------------------")
    except Exception as e:
        print(f"\nERRO CRÍTICO NA API: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai())
