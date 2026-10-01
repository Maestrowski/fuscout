import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load API key and environmental variables from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

SEASON = 2024

# 1. Premier League 
PREMIER_LEAGUE = {
    "Arsenal": 42, "Aston Villa": 66, "Bournemouth": 35, "Brentford": 55,
    "Brighton": 51, "Chelsea": 49, "Crystal Palace": 52, "Everton": 45,
    "Fulham": 36, "Ipswich": 57, "Leicester": 46, "Liverpool": 40,
    "Man City": 50, "Man United": 33, "Newcastle": 34, "Nottm Forest": 65,
    "Southampton": 41, "Tottenham": 47, "West Ham": 48, "Wolves": 39
}

# 2. Bundesliga
BUNDESLIGA = {
    "Bayern Munich": 157, "Dortmund": 165, "RB Leipzig": 173, "Leverkusen": 168,
    "Frankfurt": 169, "Stuttgart": 172, "Wolfsburg": 161, "Freiburg": 160,
    "Augsburg": 170, "Hoffenheim": 167, "Werder Bremen": 162, "Heidenheim": 180,
    "Union Berlin": 182, "Monchengladbach": 163, "Bochum": 176, "Mainz 05": 164,
    "St. Pauli": 186, "Holstein Kiel": 191
}

# 3. La Liga 
LA_LIGA = {
    "Real Madrid": 541, "Barcelona": 529, "Atletico Madrid": 530, "Athletic Club": 531,
    "Real Sociedad": 548, "Real Betis": 543, "Villarreal": 533, "Valencia": 532,
    "Sevilla": 536, "Osasuna": 727, "Girona": 547, "Celta Vigo": 538,
    "Mallorca": 798, "Rayo Vallecano": 728, "Las Palmas": 534, "Getafe": 546,
    "Alaves": 542, "Espanyol": 540, "Valladolid": 720, "Leganes": 745
}

LIGUE_1 = {
    "Paris Saint Germain": 85, "Marseille": 81, "Monaco": 91, "Lille": 79,
    "Lyon": 80, "Lens": 116, "Nice": 84, "Rennes": 94,
    "Reims": 93, "Toulouse": 96, "Montpellier": 82, "Strasbourg": 95,
    "Brest": 1063, "Nantes": 83, "Le Havre": 98, "Auxerre": 108,
    "Angers": 77, "Saint Etienne": 1061
}

SERIE_A = {
    "Inter": 505, "Juventus": 496, "AC Milan": 489, "Atalanta": 499,
    "Roma": 497, "Lazio": 487, "Napoli": 492, "Fiorentina": 502,
    "Bologna": 500, "Torino": 503, "Monza": 1579, "Genoa": 495,
    "Lecce": 867, "Verona": 504, "Udinese": 494, "Cagliari": 490,
    "Empoli": 511, "Parma": 523, "Como": 895, "Venezia": 517
}

# Fetch player data for top 5 leagues for the 2024 season
def fetch_squad_page(team_id: int, team_name: str):
    params = {"team": team_id, "season": SEASON, "page": 1}
    res = requests.get(f"{BASE_URL}/players", headers=HEADERS, params=params)
    data = res.json()
    
    if "errors" in data and data["errors"]:
        print(f"Error fetching {team_name}: {data['errors']}")
        return []
    
    players = data.get("response", [])
    print(f"{team_name} (ID {team_id}): {len(players)} players")
    return players

# Get league data to find and save player data to JSON files. 
def extract_competition(comp_name: str, teams: dict, output_file: str):
    print(f" Extracting {comp_name} ({len(teams)} clubs)")
    out_path = Path("data/raw") / output_file
    
    #Load existing records if the file already exists so we don't overwrite them
    all_players = []
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                all_players = json.load(f)
            print(f"  [i] Found {len(all_players)} existing records in {output_file}. Appending new teams...")
        except Exception:
            all_players = []

    #Fetch new teams
    for name, team_id in teams.items():
        players = fetch_squad_page(team_id, name)
        all_players.extend(players)
        time.sleep(6.5)  # Enforce <= 10 requests per minute
        
    #Save the combined dataset
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_players, f, indent=2)
    print(f"-> Saved {len(all_players)} total players to {out_path}\n")

def main():
    os.makedirs("data/raw", exist_ok=True)
    
    #extract_competition("Premier League", PREMIER_LEAGUE, "players_pl.json")
    #extract_competition("Bundesliga", BUNDESLIGA, "players_bundesliga.json")
    #extract_competition("La Liga", LA_LIGA, "players_laliga.json")
    #extract_competition("Ligue 1", LIGUE_1, "players_ligue1.json")
    extract_competition("Serie A", SERIE_A, "players_seriea.json")
    print("\nExtraction complete!")

if __name__ == "__main__":
    main()