import os
import json
import requests
from dotenv import load_dotenv

# Load API key and environmental variables from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Fetch Premier League and Eredivise player data from the 2024 season and save to data/raw 
def fetch_league_players(league_id: int, season: int = 2024, pages: int = 3):
    """
    Fetches raw player data from API-Football for a given league and season.
    Each page returns 20 player objects.
    """
    records = []
    for page in range(1, pages + 1):
        print(f"Fetching league {league_id}, season {season}, page {page}...")
        params = {"league": league_id, "season": season, "page": page}
        
        response = requests.get(f"{BASE_URL}/players", headers=HEADERS, params=params)
        data = response.json()
        
        if "errors" in data and data["errors"]:
            print(f"API Error on page {page}: {data['errors']}")
            break
            
        items = data.get("response", [])
        if not items:
            print(f"No more records returned on page {page}.")
            break
            
        records.extend(items)
        
    return records

def main():
    # Ensure data/raw directory exists
    os.makedirs("data/raw", exist_ok=True)
    
    # 1. Premier League- Season 2024 
    print("Starting extraction for Premier League...")
    pl_data = fetch_league_players(league_id=39, season=2024, pages=3)
    with open("data/raw/players_pl.json", "w", encoding="utf-8") as f:
        json.dump(pl_data, f, indent=2)
    print(f"Saved {len(pl_data)} raw records to data/raw/players_pl.json\n")
    
    # 2. Bundesliga- Season 2024 
    print("Starting extraction for German Bundesliga...")
    bundesliga_data = fetch_league_players(league_id=78, season=2024, pages=3)
    with open("data/raw/players_bundesliga.json", "w", encoding="utf-8") as f:
        json.dump(bundesliga_data, f, indent=2)
    print(f"Saved {len(bundesliga_data)} raw records to data/raw/players_bundesliga.json\n")
    
    print("Raw extraction complete.")

if __name__ == "__main__":
    main()