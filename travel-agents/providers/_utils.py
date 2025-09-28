def clamp_len(s: str, n: int = 80) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n-1] + "…"
