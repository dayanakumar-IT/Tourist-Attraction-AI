import requests
from ..settings import HTTP_TIMEOUT

def convert(amount: float, from_ccy: str, to_ccy: str) -> float:
    """Convert currency via exchangerate.host."""
    r = requests.get(
        "https://api.exchangerate.host/convert",
        params={"from": from_ccy, "to": to_ccy, "amount": amount},
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    result = r.json().get("result")
    if result is None:
        raise ValueError(f"Conversion failed {from_ccy}->{to_ccy}")
    return float(result)
