import re
from typing import Optional, Tuple
from datetime import date, timedelta
import dateparser

def _dateify(s: Optional[str]) -> Optional[str]:
    if not s: return None
    dt = dateparser.parse(s)
    return dt.date().isoformat() if dt else None

def parse_trip_free_text(text: str, today: Optional[date] = None) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[int], int]:
    """
    Extract destination, start_date, end_date, nights, adults from a single free-text prompt.
    Examples the user might type:
      - "Paris in December for 4 nights"
      - "Go to Dubai Oct 10-15, 2 adults"
      - "Tokyo next week for 3 days"
    """
    t = text.strip()

    # naive adults parse
    m_adults = re.search(r'(\d+)\s*(adult|adults|people|pax)', t, re.I)
    adults = int(m_adults.group(1)) if m_adults else 1

    # nights/days
    m_nights = re.search(r'(\d+)\s*(night|nights)', t, re.I)
    nights = int(m_nights.group(1)) if m_nights else None
    m_days = re.search(r'(\d+)\s*(day|days)', t, re.I)
    if (not nights) and m_days:
        nights = max(1, int(m_days.group(1)) - 1)

    # date window - look for ranges like "Oct 2-6" or "2025-11-02 to 2025-11-05"
    m_range = re.search(r'([A-Za-z0-9\-\/]+)\s*(?:to|\-|–|—)\s*([A-Za-z0-9\-\/]+)', t)
    start_date = _dateify(m_range.group(1)) if m_range else None
    end_date   = _dateify(m_range.group(2)) if m_range else None

    # single date like "on Oct 10"
    if not start_date:
        m_single = re.search(r'on\s+([A-Za-z0-9\-\/]+)', t, re.I)
        start_date = _dateify(m_single.group(1)) if m_single else None

    # infer end from nights
    if start_date and nights and not end_date:
        sd = date.fromisoformat(start_date)
        end_date = (sd + timedelta(days=nights)).isoformat()

    # fallback start if nights exist but date missing → use today+7
    if nights and not start_date:
        base = today or date.today()
        start_date = (base + timedelta(days=7)).isoformat()
        end_date = (base + timedelta(days=7+nights)).isoformat()

    # destination = heuristic: take first capitalized word/phrase not recognized as a date
    # (simple & forgiving)
    # Try: “… to <place> …”
    m_dest = re.search(r'(?:to|go to|visit|plan to|trip to)\s+([A-Za-z\s]+)', t, re.I)
    destination = (m_dest.group(1).strip() if m_dest else t).split(' for ')[0].split(' on ')[0]
    destination = re.sub(r'\b(in|on|at|for|from)\b.*$', '', destination, flags=re.I).strip()
    destination = destination.title() if destination else "Colombo"

    return destination, None, start_date, end_date, nights, adults
