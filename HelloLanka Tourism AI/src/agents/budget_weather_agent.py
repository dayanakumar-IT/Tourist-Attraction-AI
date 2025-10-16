import datetime as dt
from typing import List
from ..contracts import TripNormalized, Itinerary, BudgetSummary
from ..tools.geocode import geocode_nominatim
from ..tools.weather import forecast_hint
from ..tools.fx import convert
from ..settings import BASE_CCY

# Fallback multipliers for foreign tourists
MULTIPLIERS_FOREIGN = {
    "tickets": 2.5,
    "tours": 1.4,
    "transport": 1.15,
    "food": 1.05,
}

# rough per-person/day LKR bands (coastal)
BANDS_LKR = {"food": 2500, "transport": 2000, "tickets": 1500, "misc": 1000}

class BudgetWeatherAgent:
    def revise(self, req: TripNormalized, drafts: List[Itinerary]) -> List[Itinerary]:
        party = max(1, req.party.count)
        # base math currency
        # convert user's total to base for calculations
        total_in_base = convert(req.budget.amount, req.budget.currency.upper(), BASE_CCY) if req.budget.currency.upper()!=BASE_CCY else req.budget.amount
        per_day_budget_base = total_in_base / max(1, req.trip_days)

        for itin in drafts:
            # Weather pass + comfort tweaks
            for day in itin.daily_plan:
                gc = geocode_nominatim(day.base_city) or geocode_nominatim(req.start_location)
                w = forecast_hint(gc["lat"], gc["lon"], dt.date.fromisoformat(day.date)) if gc else {"summary":"unknown","rain_mm":0}
                day.weather_hint = w["summary"]
                if w["summary"] == "rainy" and day.activities:
                    # put spa/wellness earlier for rainy days
                    day.activities.sort(key=lambda a: 0 if a.kind in ("spa","wellness") else 1)
                    day.notes.append("Reordered for rain: spa moved earlier.")
                if "elderly" in (req.party.notes or "").lower():
                    day.notes.append("Added gentle pacing for elderly (rest-friendly day).")

            # Budget pass
            # Compute baseline per-day cost (base currency)
            per_day_base = sum(BANDS_LKR.values()) * party
            if req.traveler_profile == "foreign_tourist":
                per_day_base *= 0.25*MULTIPLIERS_FOREIGN["tickets"] + 0.25*MULTIPLIERS_FOREIGN["tours"] + \
                                0.25*MULTIPLIERS_FOREIGN["transport"] + 0.25*MULTIPLIERS_FOREIGN["food"]

            # Convert estimate to user currency for display
            user_ccy = req.budget.currency.upper()
            per_day_user = convert(per_day_base, BASE_CCY, user_ccy) if user_ccy!=BASE_CCY else per_day_base

            # Affordability
            afford = "Comfortable" if per_day_user <= per_day_budget_base*0.8 else \
                     ("OK" if per_day_user <= per_day_budget_base*1.2 else "Tight")

            itin.budget_summary = BudgetSummary(
                currency=user_ccy,
                per_day_estimate=int(per_day_user),
                breakdown={"food":"med","transport":"car/train","tickets":"low","misc":"med"},
                affordability=afford
            )

            # Constraints notes
            if "allergy" in (req.party.notes or "").lower():
                if "constraints_notes" not in itin.model_fields_set:
                    itin.constraints_notes = []
                itin.constraints_notes.append("Food allergy: prefer restaurants with allergen info.")
        return drafts
