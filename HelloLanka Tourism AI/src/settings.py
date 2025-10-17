
# src/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM (Gemini, OpenAI-compatible) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# Google’s OpenAI-compatible base (chat/completions)
GEMINI_BASE    = os.getenv("GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/")

# --- External data APIs ---
# external keys
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")   # optional

# --- Net / etiquette ---
USER_AGENT   = "HelloLanka-TourismAI/0.1 (contact: you@example.com)"

# timeouts
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "15"))

# --- App defaults ---
BASE_CCY = "LKR"  # internal math currency




