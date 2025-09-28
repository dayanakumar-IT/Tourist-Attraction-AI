import os, requests
from dotenv import load_dotenv

load_dotenv()

AMADEUS_BASE = "https://test.api.amadeus.com"

def get_token():
    r = requests.post(
        f"{AMADEUS_BASE}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.getenv("AMADEUS_CLIENT_ID"),
            "client_secret": os.getenv("AMADEUS_CLIENT_SECRET"),
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]

def test_city_search(city="Tokyo"):
    token = get_token()
    r = requests.get(
        f"{AMADEUS_BASE}/v1/reference-data/locations",
        headers={"Authorization": f"Bearer {token}"},
        params={"keyword": city, "subType": "CITY"},
    )
    print("City search:", r.status_code, r.json())

def test_hotels(city_code="TYO"):
    token = get_token()
    r = requests.get(
        f"{AMADEUS_BASE}/v3/shopping/hotel-offers",
        headers={"Authorization": f"Bearer {token}"},
        params={"cityCode": city_code, "adults": 1, "checkInDate": "2025-10-01", "checkOutDate": "2025-10-05"},
    )
    print("Hotels:", r.status_code, r.json())

if __name__ == "__main__":
    test_city_search()
    test_hotels()
