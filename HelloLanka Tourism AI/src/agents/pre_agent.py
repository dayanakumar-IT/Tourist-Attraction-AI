import json, requests
from typing import List, Tuple
from ..settings import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE

CONTROLLED = ["beach","spa","adventure","culture","nature","food","wellness","wildlife","photography","mixed_highlights"]

def _call_gemini_normalize(raws: List[str]) -> List[str]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing; cannot normalize themes with LLM.")

    url = GEMINI_BASE.rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GEMINI_API_KEY}"}

    prompt = (
        "You map arbitrary user travel interests to normalized themes from this fixed set: "
        f"{CONTROLLED}. Return ONLY a JSON list of themes (no prose, no explanation). "
        "If an input implies multiple themes, include all relevant ones."
    )

    user = ", ".join(raws)
    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
    }

    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]

    # Extract JSON array defensively
    start = content.find("[")
    end   = content.rfind("]")+1
    if start == -1 or end <= start:
        raise ValueError(f"Gemini returned unexpected content (no JSON array): {content!r}")

    parsed = json.loads(content[start:end])

    if not isinstance(parsed, list):
        raise ValueError(f"Gemini returned non-list: {parsed!r}")

    out = [t for t in parsed if t in CONTROLLED]
    if not out:
        raise ValueError(f"Gemini returned no valid themes from {parsed!r}")
    return out

def normalize_themes(themes_raw: List[str], free_text_interest: str|None) -> List[str]:
    raws = list(themes_raw or [])
    if free_text_interest:
        raws.append(free_text_interest)
    if not raws:
        raise ValueError("No themes or interest text provided. Frontend must send something to normalize.")
    return _call_gemini_normalize(raws)

def infer_traveler_profile(currency: str, override: str|None) -> Tuple[str, str]:
    # This is a simple rule, not a price heuristic.
    if override in ("local_or_expat","foreign_tourist"):
        return override, "explicit_override"
    if currency.upper() != "LKR":
        return "foreign_tourist", "currency_inference"
    return "local_or_expat", "currency_inference"
