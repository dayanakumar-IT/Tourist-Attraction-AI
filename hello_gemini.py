# hello_gemini.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env.")

client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

resp = client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[{
        "role": "user",
        "content": "Suggest 3 free or low-cost student-friendly attractions in Kandy."
    }]
)

print(resp.choices[0].message)
