import argparse
import json
import sys

from .graph_pipeline import run_graph


def _ascii(s: str) -> str:
	try:
		return s.encode("ascii", errors="ignore").decode("ascii")
	except Exception:
		return s


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--input", default="src/input_demo.json")
	ap.add_argument("--trace", action="store_true")
	args = ap.parse_args()

	try:
		with open(args.input, "r", encoding="utf-8") as f:
			payload = json.load(f)
	except Exception as e:
		print(f"Failed to read input JSON: {e}")
		sys.exit(1)

    result = run_graph(payload, trace=args.trace)

	print("\n=== RESULT (3 plans max) ===")
	for i, plan in enumerate(result.get("plans", [])[:3], 1):
		title_ascii = _ascii((plan.get('title') or '').replace('–', '-').replace('—', '-'))
		print(f"\n--- PLAN {i}: {title_ascii} [{', '.join(plan.get('theme_mix', []))}]")
		print("Budget:", plan.get("budget_summary"))
		for d in plan.get("daily_plan", []):
			print(f"  {d['date']} - {_ascii(d['base_city'])} (weather: {d.get('weather_hint','?')})")
			for leg in d.get("travel_legs", []):
				f_from = leg.get("from") or leg.get("from_") or leg.get("from")
				print(f"     travel: {leg.get('mode','?')} {_ascii(str(f_from))} -> {_ascii(str(leg.get('to','?')))} ~ {leg.get('eta_min','?')} min ({leg.get('km','?')} km)")
			for a in d.get("activities", []):
				print(f"     activity: {a['start']} {_ascii(a['name'])} ({_ascii(a['kind'])}) ~ {a['duration_min']} min")
			for n in d.get("notes", []):
				print(f"     note: {_ascii(n)}")
	print("\nDone.")


if __name__ == "__main__":
	main()


