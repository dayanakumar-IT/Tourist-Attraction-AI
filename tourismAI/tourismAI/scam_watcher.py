# scam_watcher.py
import asyncio
from urllib.parse import urlparse
from schemas import PlannerPayload, ScamWatcherResponse, CheckResult, Item
import live_sources as live

def _https_check(url: str) -> tuple[int, list[str]]:
    if not url:
        return 0, ["no_url"]
    if urlparse(url).scheme != "https":
        return 10, ["No HTTPS"]
    return 0, []

async def _score_item_async(payload_city: str, it: Item) -> CheckResult:
    risk, signals, alts = 0, [], []

    # 1) URL basic & Safe Browsing
    r, s = _https_check(it.url or "")
    risk += r
    signals += s
    domain = None
    if it.url:
        domain = live.extract_domain(it.url)

        # Safe Browsing
        gsb = await live.gsb_is_malicious(it.url)
        if gsb is True:
            risk += 60
            signals.append("URL flagged by Safe Browsing")

        # RDAP domain age
        if domain:
            age = await live.rdap_domain_age_days(domain)
            if age is not None and age < 90:
                risk += 20
                signals.append(f"Domain very new ({age} days)")

        # Tiny heuristic: domains advertising extreme bargains
        if domain and any(k in domain for k in ["cheap", "cheep", "deal", "discount", "supercheep"]):
            risk += 5
            signals.append("Suspicious bargain keyword in domain")

    # 2) Price sanity via Google Places price_level
    #    If we don't have item price, we still compute a "median" for messages.
    median = await live.google_place_price_median(it.city or payload_city, it.name)
    if median is not None and it.price is not None and it.price < 0.5 * median:
        risk += 25
        signals.append(f"Too cheap vs typical median ~{median:.2f}")

    # 3) Payment method red flags (strong + soft)
    pm = [p.lower() for p in (it.payment_methods or [])]

    risky_methods = {"whatsapp", "bank transfer", "gift card", "crypto"}
    if any(m in risky_methods for m in pm):
        risk += 30
        signals.append("Risky payment method")

    # Soft warning: cash-only (no card option) → harder to dispute or refund
    if "cash" in pm and not any(m in {"card", "credit card", "debit card", "visa", "mastercard"} for m in pm):
        risk += 10
        signals.append("Cash-only — limited refund/receipt protection")

    # 4) Review spam (quick heuristic)
    if it.reviews:
        text = " ".join(it.reviews).lower()
        # super tiny heuristic: repeated 4+ same-word sequences
        words = text.split()
        repeats = sum(1 for i in range(max(0, len(words) - 5)) if words[i:i + 6] == words[i + 1:i + 7])
        if repeats > 3:
            risk += 25
            signals.append("Reviews look repetitive/unnatural")

    # Alternatives
    official = await live.google_place_official_website(it.city or payload_city, it.name)
    if official:
        alts.append(official)
    elif ("No HTTPS" in signals or
          any("Too cheap" in s for s in signals) or
          "Cash-only — limited refund/receipt protection" in signals):
        alts.append("Buy at official counter / verified tourism portal")

    return CheckResult(item=it.name, risk=min(int(risk), 100), signals=signals, alternatives=alts)

async def score_payload_async(payload: PlannerPayload) -> ScamWatcherResponse:
    tasks = [asyncio.create_task(_score_item_async(payload.city, it)) for it in payload.items]
    checks = await asyncio.gather(*tasks)
    return ScamWatcherResponse(checks=checks)

# sync wrapper (safe): only use when NOT already inside an event loop
def score_payload(payload: PlannerPayload) -> ScamWatcherResponse:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(score_payload_async(payload))
    else:
        raise RuntimeError(
            "score_payload() called inside a running event loop. "
            "Use 'await score_payload_async(...)' instead."
        )
