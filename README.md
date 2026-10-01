## What I built and who for

I built a CLI-based football player scouting and benchmark tool. This project analyses a teams weakness in specific positions and suggests the correct fit of players as potential transfer targets. This is mainly a data engineerined scouting tool which would be used by professional football scouts across the top 5 european leagues, where they would obtain the data report and then decide to further analyse the reported player. This can also be used by recruitment analysts that can use this tool to evaluate their transfer strategies. 

## The data
* **API Used:** [API-Football (v3)](https://www.api-football.com/)
* **Documentation Link:** (https://www.api-football.com/documentation-v3)
* **What was gathered:**
* Endpoint: `/players` for the 2024 season across Europe's Big 5 domestic leagues:
    * Premier League (ID: `39`)
    * La Liga (ID: `140`)
    * Serie A (ID: `135`)
    * Bundesliga (ID: `78`)
    * Ligue 1 (ID: `61`)
  * **Payload Details:** Core demographic metadata (player name, age, nationality, primary club) and granular season match statistics covering offensive output (goals, shots on target), distribution (total passes, key passes), defensive actions (tackles, interceptions, blocks, duels won), discipline (fouls committed, yellow/red cards), goalkeeping (saves, goals conceded), match appearances, minutes played, and match ratings across competitions.
  * **Caching Strategy:** The raw API responses are stored locally as JSON files (`data/raw/*.json`) to avoid rate-limiting issues, ensure instant offline execution, and allow reproducible zero-setup evaluation.

### 1. Data Processing & Modeling (DuckDB)
* **Ingestion:** DuckDB's native JSON reader (`read_json_auto`) ingests the nested JSON files directly into an in-memory staging table without external database infrastructure.
* **Unnesting & League Isolation:** A player's `statistics` array often contains domestic cups, European tournaments, and prior clubs. The pipeline unnests all entries and filters strictly for domestic league minutes in the Big 5 leagues.
* **Data Hygiene & Decoding:** HTML entity artifacts in player names (`&apos;`, `&#039;`, `&amp;`) are parsed and cleaned.
* **Player-Level Deduplication & Stint Aggregation:** Players who transferred mid-season (e.g., Nicolò Fagioli playing for both Juventus and Fiorentina) are aggregated by `player_id`. Counting metrics are summed, per-90 metrics are recalculated over their total accumulated minutes, and the player is mapped to the club where they logged the most minutes.
* **Sample-Size Filter:** A hard filter requiring $\ge 450$ minutes played is applied to eliminate small-sample noise.

### 2. Analytical Methodology & Scoring Formula
* **Minutes-Weighted Ratings:** Match ratings across appearances are computed as a minutes-weighted average:
  $$\text{Rating}_{\text{weighted}} = \frac{\sum (\text{rating}_i \times \text{minutes}_i)}{\sum \text{minutes}_i}$$
* **Per-90 Normalization:** Counting metrics are converted to per-90 rates:
  $$\text{Rate}_{\text{per 90}} = \left(\frac{\text{Count}}{\text{Minutes}}\right) \times 90$$
* **17 Tactical Sub-Roles:** Main positions (Attacker, Midfielder, Defender, Goalkeeper) map to specialized roles with tailored metrics and weights (e.g., *Destroyer* weights Tackles/90 [45%], Interceptions/90 [40%], and Fouls/90 [15%]).
* **Deficit-Weighted Upgrade Score:** To avoid identical rankings across clubs, candidates are scored using relative percentage uplift over the user club's baseline average ($B$):
  $$\text{Composite Upgrade Score} = \sum_{i=1}^{3} \left( w_i \times \frac{M_{\text{candidate}, i} - B_{\text{club}, i}}{\max(B_{\text{club}, i}, 0.05)} \right) \times 100$$
  This ensures that if a squad already has high tackle rates but low interceptions, the algorithm dynamically prioritizes lane-reading interceptors over redundant ball-winners.

### 3. Application Workflow
* **TUI State Machine:** Built using `questionary` and `tabulate`.
* Steps:
  1. Select target club's domestic league and club.
  2. Choose scouting feeder pool (all Big 5 leagues or a specific league).
  3. Set optional minimum and maximum age filters.
  4. Select position and tactical sub-role.
  5. Inspect target squad's baseline player table alongside the Top 10 ranked targets.
  6. Drill down into individual candidate dossiers or pivot to another position/search.

## How to run it.

### Prerequisites
* Python 3.10+
* Virtual environment tool (`venv`)

### Reproduction Steps

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd fuscout

2. **Create and activate a virtual environment**
On Windows
    python -m venv .venv
    .venv\Scripts\Activate.ps1

3. **Install dependencies**

pip install -r requirements.txt

4. Launch the application

python main.py

## What I would do next

I would integrate market values, wage estimates and contract expiration dates to assess if the player is affordable for a set club, for example Brighton wouldn't be able to afford a player like Vinicius Jr.

Player similarity rader: Allow a way to look for players with a similiar profile to current players at a club. So for example if Manchester United wanted to replace Harry Maguire, they would look for players with similiar statistics

Provide CSV reports as output for future use

## Where AI helped

With tedious tasks where I would have to write down metrics on what should be looked for in 17 different tactical positions (Instead of manually writing down every metric for 17 tactical positions I would list the requirements and have the AI generate the code for the metrics)

Also referred to AI for help with how to calculate the scoring formula metrics.

Used AI to gather club IDs from Football-API for data fetching purposes. 
