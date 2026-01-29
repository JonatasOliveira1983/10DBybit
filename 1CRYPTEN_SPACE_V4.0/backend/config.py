from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings(BaseSettings):
    # Firebase (Google)
    FIREBASE_CREDENTIALS_PATH: str = "serviceAccountKey.json"
    FIREBASE_DATABASE_URL: Optional[str] = None

    # Bybit
    BYBIT_API_KEY: Optional[str] = None
    BYBIT_API_SECRET: Optional[str] = None
    BYBIT_CATEGORY: str = "linear"
    BYBIT_CATEGORY: str = "linear"
    BYBIT_TESTNET: bool = False # FALSE = Mainnet Data (Real Prices)
    BYBIT_EXECUTION_MODE: str = "PAPER" # "PAPER" = Virtual Execution
    BYBIT_SIMULATED_BALANCE: float = 100.0 # Virtual $100

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    
    # GLM (ZhipuAI)
    GLM_API_KEY: Optional[str] = None
    
    # OpenRouter (New Primary)
    OPENROUTER_API_KEY: Optional[str] = None

    # App Logic
    DEBUG: bool = True
    PORT: int = 5001
    HOST: str = "0.0.0.0"
    MAX_SLOTS: int = 10
    RISK_CAP_PERCENT: float = 0.20
    LEVERAGE: int = 50
    INITIAL_SLOTS: int = 4
    BREAKEVEN_TRIGGER_PERCENT: float = 2.5 # 2.5% profit triggers move to entry
    
    # Fast API context
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
