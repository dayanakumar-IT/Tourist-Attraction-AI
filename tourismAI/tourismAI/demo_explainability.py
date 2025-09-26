from schemas import PlannerPayload
from scam_watcher import score_payload
from safety_policy import merge_and_explain

def main():
    payload = PlannerPayload(
        city="Kandy",
        country="LK",
        date="2025-10-12",
        items=[
            {"name":"Temple of the Tooth ticket", "url":"http://tooth-temple.shop", "price":5.0, "payment_methods":["whatsapp"]},
            {"name":"Colombo city tuk-tuk tour", "url":"https://supercheep-tours.com", "price":8.0, "payment_methods":["cash"]}
        ]
    )
    checks = score_payload(payload)              # Scam Watcher (LIVE APIs)
    report = merge_and_explain(payload, checks)  # Safety/Policy (+ explainability)

    print("\n=== SAFETY REPORT ===")
    print("Badge:", report.badge)
    print("\nReasons:");        [print(" -", r) for r in report.reasons]
    print("\nPolicy notes:");   [print(" -", p) for p in report.policy_notes]
    print("\nSafety tips:");    [print(" -", s) for s in report.safety_tips]
    print("\nAlternatives:");   [print(" -", a) for a in report.alternatives]

if __name__ == "__main__":
    main()
