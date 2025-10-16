from dotenv import load_dotenv; load_dotenv()
import os

# --- LLM (Gemini, OpenAI-compatible) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
# Google’s OpenAI-compatible base (chat/completions)
GEMINI_BASE    = os.getenv("GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta/openai/")

# --- External data APIs ---
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")   # optional
OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY", "")   # optional

# --- Net / etiquette ---
USER_AGENT   = "HelloLanka-TourismAI/0.1 (contact: you@example.com)"
HTTP_TIMEOUT = 15

# --- App defaults ---
BASE_CCY = "LKR"  # internal math currency
