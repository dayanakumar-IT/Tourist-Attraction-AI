import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

# Create client for Gemini (OpenAI-compatible endpoint)
client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# Send a simple test message
resp = client.chat.completions.create(
    model="gemini-2.5-flash",  # or gemini-2.5-pro if you want
    messages=[{"role": "user", "content": "Suggest 3 tourist attractions in Kandy under 5000 LKR"}]
)

print(resp.choices[0].message)
