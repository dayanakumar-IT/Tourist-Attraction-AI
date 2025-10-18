import argparse
import json
import sys

from .agent_graph import run_multiagent


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

	result = run_multiagent(payload, trace=args.trace)

	print("\n=== OPTIMIZED SRI LANKA TOURISM PLAN ===")
	
	# Display the single optimized plan with enhanced data
	for i, plan in enumerate(result.get("plans", [])[:1], 1):
		title_ascii = _ascii((plan.get('title') or '').replace('–', '-').replace('—', '-'))
		print(f"\n🎯 {title_ascii} [{', '.join(plan.get('theme_mix', []))}]")
		print("💰 Budget:", plan.get("budget_summary"))
		
		total_cost = 0
		for d in plan.get("daily_plan", []):
			# Get weather for the day
			day_weather = "unknown"
			if d.get('weather_hint'):
				day_weather = d['weather_hint']
			elif d.get('activities'):
				first_activity = d['activities'][0]
				if isinstance(first_activity, dict) and first_activity.get('weather_info'):
					weather = first_activity['weather_info']
					day_weather = f"{weather.get('summary', 'unknown')} ({weather.get('temperature', '?')}°C)"
			
			print(f"\n📅 {d['date']} - {_ascii(d['base_city'])}")
			print(f"🌤️  Weather: {day_weather}")
			
			# Show travel legs with costs
			day_cost = 0
			for leg in d.get("travel_legs", []):
				# Handle both dict and Pydantic object
				if hasattr(leg, 'model_dump'):
					leg_dict = leg.model_dump(by_alias=True, mode="json")
				else:
					leg_dict = leg
				
				f_from = leg_dict.get("from") or leg_dict.get("from_") or leg_dict.get("from")
				cost = leg_dict.get('estimated_cost', 0) or 0
				currency = leg_dict.get('cost_currency', 'LKR')
				day_cost += cost
				cost_display = f" 💰 {cost} {currency}" if cost > 0 else ""
				print(f"🚗 Travel: {leg_dict.get('mode','?')} {_ascii(str(f_from))} → {_ascii(str(leg_dict.get('to','?')))} ~ {leg_dict.get('eta_min','?')} min ({leg_dict.get('km','?')} km){cost_display}")
			
			total_cost += day_cost
			
			# Show activities with enhanced data
			for a in d.get("activities", []):
				print(f"\n🎯 {a['start']} - {_ascii(a['name'])} ({_ascii(a['kind'])}) ~ {a['duration_min']} min")
				
				# Show weather info
				if isinstance(a, dict) and a.get('weather_info'):
					weather = a['weather_info']
					print(f"   🌤️  Weather: {weather.get('summary', 'unknown')} | Temp: {weather.get('temperature', '?')}°C | Humidity: {weather.get('humidity', '?')} | Wind: {weather.get('wind', '?')}")
				
				# Show nearby restaurants
				if isinstance(a, dict) and a.get('nearby_restaurants'):
					rest_list = a['nearby_restaurants']
					print(f"   🍽️  Nearby Restaurants ({len(rest_list)} found):")
					for rest in rest_list[:3]:  # Show top 3
						rating = rest.get('rating', '?')
						rating_display = f" ⭐ {rating}" if rating != '?' else ""
						print(f"      • {_ascii(rest.get('name', 'Unknown'))}{rating_display}")
				
				# Show timing info
				if isinstance(a, dict) and a.get('timing_info'):
					timing = a['timing_info']
					print(f"   ⏰ Best time: {timing.get('best_time', '09:00-17:00')}")
			
			# Show notes
			for n in d.get("notes", []):
				print(f"   📝 Note: {_ascii(n)}")
		
		# Show total cost summary
		if total_cost > 0:
			print(f"\n💰 Total Estimated Transport Cost: {total_cost} LKR")

	print("\n✅ Done! This is your optimized Sri Lanka tourism plan with weather, food, and transport enhancements.")


if __name__ == "__main__":
	main()


