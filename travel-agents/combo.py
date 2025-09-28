from typing import List, Optional, Tuple
from schemas import FlightOption, HotelOption, ComboOption, ComboReason, FinalCombos

FX_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "CAD": 0.73,
    "AUD": 0.67,
    "LKR": 0.0033,
}

def to_usd(amount: float, ccy: Optional[str]) -> Tuple[float, Optional[str]]:
    c = (ccy or "USD").upper()
    rate = FX_TO_USD.get(c)
    if rate is None or rate <= 0:
        return amount, f"No FX rate for {c} — treated as USD for display"
    return amount * rate, None

def reason_for_combo(idx: int, f: FlightOption, h: HotelOption) -> ComboReason:
    pros, cons = [], []
    direct_out = f.is_direct_outbound is True
    direct_ret = f.is_direct_return is True

    if direct_out and direct_ret:
        why = "Fast and simple: direct both ways, minimal hassle."
    elif direct_out or direct_ret:
        why = "Balanced: one leg is direct, the other has a short connection."
    else:
        why = "Value-focused pick with reasonable connections."

    # Slight variation by rank
    if idx == 0:
        pros.append("Cheapest overall among the options shown")
    elif idx == 1:
        pros.append("Great value with slightly different timing")
    else:
        pros.append("Alternative timing that may suit your schedule better")

    pros.append(f"Airline: {f.airline or 'Mixed'}")

    # Duration hints
    if f.duration_outbound_iso:
        pros.append(f"Outbound duration approx. {f.duration_outbound_iso}")
    if f.duration_return_iso:
        pros.append(f"Return duration approx. {f.duration_return_iso}")

    return ComboReason(why_together=why, pros=pros, cons=cons or ["Exchange rate is approximate"])

def make_combos(destination: str, date_window: str,
                flights: List[FlightOption],
                hotels: List[HotelOption]) -> FinalCombos:
    combos: List[ComboOption] = []

    flights_sorted = sorted(flights, key=lambda f: f.price_total if f.price_total is not None else 9e9)[:3]
    hotels_sorted = sorted(hotels, key=lambda h: h.price_total)[:3]

    for i in range(min(3, len(flights_sorted), len(hotels_sorted))):
        f, h = flights_sorted[i], hotels_sorted[i]
        f_usd, f_note = to_usd(f.price_total, f.price_currency)
        h_usd, h_note = to_usd(h.price_total, h.price_currency)
        total_usd = round((f_usd + h_usd), 2)

        reasons = reason_for_combo(i, f, h)
        if f_note: reasons.cons.append(f_note)
        if h_note: reasons.cons.append(h_note)

        combos.append(ComboOption(
            title=f"Combo {i+1}: {f.summary} + {h.name}",
            flight=f,
            hotel=h,
            est_total_usd=total_usd,
            currency="USD",
            reasons=reasons
        ))

    return FinalCombos(destination=destination, date_window=date_window, combos=combos)
