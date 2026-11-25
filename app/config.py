"""Application settings."""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME = "SourceWise AI"
    APP_VERSION = "1.0.0"
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    MAX_SUPPLIERS = int(os.getenv("MAX_SUPPLIERS", "5"))

settings = Settings()
