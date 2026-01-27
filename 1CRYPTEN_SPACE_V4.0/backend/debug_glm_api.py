from zhipuai import ZhipuAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GLM_API_KEY")

def debug_glm():
    print(f"Testing API Key: {api_key[:5]}...{api_key[-5:]}")
    client = ZhipuAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="glm-4-plus",
            messages=[{"role": "user", "content": "Ping"}],
        )
        print("Success!")
        print(response)
    except Exception as e:
        print("\n--- API ERROR DETECTED ---")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        
        # Try to extract more details if it's a ZhipuAI error
        if hasattr(e, 'status_code'):
            print(f"HTTP Status Code: {e.status_code}")
        if hasattr(e, 'response'):
            print(f"Response Body: {e.response.text}")

if __name__ == "__main__":
    debug_glm()
