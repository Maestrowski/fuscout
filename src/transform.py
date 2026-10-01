import os
import duckdb
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

# Define statistical definitions and weights for each sub-role
ROLE_METRIC_MAP = {
    # Attackers
    "Poacher": {
        "position": "Attacker",
        "metrics": ["goals_per_90", "shots_on_target_per_90", "shot_accuracy"],
        "weights": [0.45, 0.35, 0.20],
        "higher_is_better": [True, True, True]
    },
    "Target Man": {
        "position": "Attacker",
        "metrics": ["duels_won_per_90", "goals_per_90", "fouls_drawn_per_90"],
        "weights": [0.40, 0.35, 0.25],
        "higher_is_better": [True, True, True]
    },
    "Inside Forward": {
        "position": "Attacker",
        "metrics": ["goals_per_90", "shots_per_90", "key_passes_per_90"],
        "weights": [0.40, 0.30, 0.30],
        "higher_is_better": [True, True, True]
    },
    "Winger": {
        "position": "Attacker",
        "metrics": ["key_passes_per_90", "assists_per_90", "duels_won_per_90"],
        "weights": [0.40, 0.35, 0.25],
        "higher_is_better": [True, True, True]
    },
    "False Nine": {
        "position": "Attacker",
        "metrics": ["key_passes_per_90", "assists_per_90", "passes_per_90"],
        "weights": [0.40, 0.35, 0.25],
        "higher_is_better": [True, True, True]
    },
    "Center Forward": {
        "position": "Attacker",
        "metrics": ["goals_per_90", "shots_on_target_per_90", "key_passes_per_90"],
        "weights": [0.45, 0.35, 0.20],
        "higher_is_better": [True, True, True]
    },

    # Midfielders
    "Destroyer": {
        "position": "Midfielder",
        "metrics": ["tackles_per_90", "interceptions_per_90", "fouls_committed_per_90"],
        "weights": [0.45, 0.40, 0.15],
        "higher_is_better": [True, True, True]
    },
    "Box-to-Box": {
        "position": "Midfielder",
        "metrics": ["tackles_per_90", "key_passes_per_90", "goals_per_90"],
        "weights": [0.35, 0.35, 0.30],
        "higher_is_better": [True, True, True]
    },
    "Deep Lying Playmaker": {
        "position": "Midfielder",
        "metrics": ["passes_per_90", "pass_accuracy", "interceptions_per_90"],
        "weights": [0.40, 0.35, 0.25],
        "higher_is_better": [True, True, True]
    },
    "Advanced Playmaker": {
        "position": "Midfielder",
        "metrics": ["key_passes_per_90", "assists_per_90", "passes_per_90"],
        "weights": [0.45, 0.35, 0.20],
        "higher_is_better": [True, True, True]
    },
    "Shadow Striker": {
        "position": "Midfielder",
        "metrics": ["goals_per_90", "shots_on_target_per_90", "key_passes_per_90"],
        "weights": [0.45, 0.30, 0.25],
        "higher_is_better": [True, True, True]
    },

    # Defenders
    "Ball playing center back": {
        "position": "Defender",
        "metrics": ["passes_per_90", "pass_accuracy", "interceptions_per_90"],
        "weights": [0.35, 0.35, 0.30],
        "higher_is_better": [True, True, True]
    },
    "Stopper": {
        "position": "Defender",
        "metrics": ["tackles_per_90", "duels_won_per_90", "blocks_per_90"],
        "weights": [0.40, 0.35, 0.25],
        "higher_is_better": [True, True, True]
    },
    "Attacking full back": {
        "position": "Defender",
        "metrics": ["key_passes_per_90", "assists_per_90", "tackles_per_90"],
        "weights": [0.40, 0.30, 0.30],
        "higher_is_better": [True, True, True]
    },
    "Defensive full back": {
        "position": "Defender",
        "metrics": ["tackles_per_90", "interceptions_per_90", "duels_won_per_90"],
        "weights": [0.40, 0.35, 0.25],
        "higher_is_better": [True, True, True]
    },
    "Wing back": {
        "position": "Defender",
        "metrics": ["key_passes_per_90", "tackles_per_90", "duels_won_per_90"],
        "weights": [0.40, 0.30, 0.30],
        "higher_is_better": [True, True, True]
    },

    # Goalkeeper
    "Goalkeeper": {
        "position": "Goalkeeper",
        "metrics": ["saves_per_90", "conceded_per_90", "pass_accuracy"],
        "weights": [0.50, 0.30, 0.20],
        "higher_is_better": [True, False, True]  # Low conceded is better
    }
}


def connectDuckDB():
    return duckdb.connect()


def playerModel(con: duckdb.DuckDBPyConnection):
    raw_files_pattern = str(RAW_DATA_DIR / "*.json").replace("\\", "/")

    con.execute(f"""
        CREATE OR REPLACE VIEW stg_raw_players AS 
        SELECT * FROM read_json_auto('{raw_files_pattern}');
    """)

    con.execute("""
        CREATE OR REPLACE TABLE fct_player_stats AS 
        SELECT 
            CAST(player.id AS BIGINT) AS player_id,
            CAST(player.name AS VARCHAR) AS player_name,
            CAST(COALESCE(player.age, 0) AS INTEGER) AS age,
            CAST(statistics[1].team.name AS VARCHAR) AS team_name,
            CAST(statistics[1].league.name AS VARCHAR) AS league_name,
            CAST(COALESCE(statistics[1].games.position, 'Unknown') AS VARCHAR) AS position,
            CAST(COALESCE(statistics[1].games.appearences, 0) AS INTEGER) AS appearances,
            CAST(COALESCE(statistics[1].games.minutes, 0) AS INTEGER) AS minutes_played,

            -- Overall Weighted Average Match Rating across all competitions
            ROUND(
                COALESCE(
                    list_sum(
                        list_transform(
                            list_filter(statistics, x -> x.games.rating IS NOT NULL AND x.games.minutes IS NOT NULL AND x.games.minutes > 0),
                            x -> CAST(x.games.rating AS FLOAT) * CAST(x.games.minutes AS FLOAT)
                        )
                    ) / 
                    NULLIF(
                        list_sum(
                            list_transform(
                                list_filter(statistics, x -> x.games.rating IS NOT NULL AND x.games.minutes IS NOT NULL AND x.games.minutes > 0),
                                x -> CAST(x.games.minutes AS FLOAT)
                            )
                        ), 0
                    ),
                    CAST(statistics[1].games.rating AS FLOAT),
                    0.0
                ),
                2
            ) AS match_rating,
            
            -- Raw Core Metrics
            CAST(COALESCE(statistics[1].goals.total, 0) AS INTEGER) AS total_goals,
            CAST(COALESCE(statistics[1].goals.assists, 0) AS INTEGER) AS total_assists,
            CAST(COALESCE(statistics[1].goals.conceded, 0) AS INTEGER) AS goals_conceded,
            CAST(COALESCE(statistics[1].goals.saves, 0) AS INTEGER) AS total_saves,
            CAST(COALESCE(statistics[1].shots.total, 0) AS INTEGER) AS total_shots,
            CAST(COALESCE(statistics[1].shots.on, 0) AS INTEGER) AS total_shots_on,
            CAST(COALESCE(statistics[1].passes.total, 0) AS INTEGER) AS total_passes,
            CAST(COALESCE(statistics[1].passes.key, 0) AS INTEGER) AS total_key_passes,
            CAST(COALESCE(statistics[1].passes.accuracy, 0) AS FLOAT) AS pass_accuracy,
            CAST(COALESCE(statistics[1].tackles.total, 0) AS INTEGER) AS total_tackles,
            CAST(COALESCE(statistics[1].tackles.interceptions, 0) AS INTEGER) AS total_interceptions,
            CAST(COALESCE(statistics[1].tackles.blocks, 0) AS INTEGER) AS total_blocks,
            CAST(COALESCE(statistics[1].duels.won, 0) AS INTEGER) AS total_duels_won,
            CAST(COALESCE(statistics[1].fouls.committed, 0) AS INTEGER) AS total_fouls_committed,
            CAST(COALESCE(statistics[1].fouls.drawn, 0) AS INTEGER) AS total_fouls_drawn,
            CAST(COALESCE(statistics[1].cards.yellow, 0) AS INTEGER) AS total_yellow_cards,
            CAST(COALESCE(statistics[1].cards.red, 0) AS INTEGER) AS total_red_cards,

            -- Derived Per-90 Metrics
            ROUND((CAST(COALESCE(statistics[1].goals.total, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS goals_per_90,
            ROUND((CAST(COALESCE(statistics[1].goals.assists, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS assists_per_90,
            ROUND((CAST(COALESCE(statistics[1].goals.saves, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS saves_per_90,
            ROUND((CAST(COALESCE(statistics[1].goals.conceded, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS conceded_per_90,
            ROUND((CAST(COALESCE(statistics[1].shots.total, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS shots_per_90,
            ROUND((CAST(COALESCE(statistics[1].shots.on, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS shots_on_target_per_90,
            ROUND((CAST(COALESCE(statistics[1].passes.total, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS passes_per_90,
            ROUND((CAST(COALESCE(statistics[1].passes.key, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS key_passes_per_90,
            ROUND((CAST(COALESCE(statistics[1].tackles.total, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS tackles_per_90,
            ROUND((CAST(COALESCE(statistics[1].tackles.interceptions, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS interceptions_per_90,
            ROUND((CAST(COALESCE(statistics[1].tackles.blocks, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS blocks_per_90,
            ROUND((CAST(COALESCE(statistics[1].duels.won, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS duels_won_per_90,
            ROUND((CAST(COALESCE(statistics[1].fouls.committed, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS fouls_committed_per_90,
            ROUND((CAST(COALESCE(statistics[1].fouls.drawn, 0) AS FLOAT) / NULLIF(statistics[1].games.minutes, 0)) * 90.0, 2) AS fouls_drawn_per_90,
            
            -- Accuracy Ratios
            ROUND((CAST(COALESCE(statistics[1].shots.on, 0) AS FLOAT) / NULLIF(statistics[1].shots.total, 0)) * 100.0, 1) AS shot_accuracy

        FROM stg_raw_players
        WHERE statistics[1].games.minutes IS NOT NULL
          AND statistics[1].games.minutes >= 450;
    """)


def getAvailableClubs(con: duckdb.DuckDBPyConnection, league_name: str) -> list:
    """Returns all clubs available in a specific league."""
    df = con.execute("""
        SELECT DISTINCT team_name 
        FROM fct_player_stats 
        WHERE league_name ILIKE $league
        ORDER BY team_name ASC;
    """, {"league": f"%{league_name}%"}).fetchdf()
    return df["team_name"].tolist()


def getAvailableLeagues(con: duckdb.DuckDBPyConnection) -> list:
    """Returns all distinct leagues stored in DuckDB."""
    df = con.execute("""
        SELECT DISTINCT league_name 
        FROM fct_player_stats 
        ORDER BY league_name ASC;
    """).fetchdf()
    return df["league_name"].tolist()


def scoutingShortlist(
    con: duckdb.DuckDBPyConnection, 
    target_club: str, 
    feeder_league: str, 
    sub_role: str,
    min_age: int = None,
    max_age: int = None,
    limit: int = 10
):
    """
    Parametric scouting engine that benchmarks candidate players on the specific
    metrics defining their tactical sub-role.
    """
    if sub_role not in ROLE_METRIC_MAP:
        raise ValueError(f"Unknown sub-role '{sub_role}'. Available roles: {list(ROLE_METRIC_MAP.keys())}")

    role_config = ROLE_METRIC_MAP[sub_role]
    pos = role_config["position"]
    m1, m2, m3 = role_config["metrics"]
    w1, w2, w3 = role_config["weights"]
    h1, h2, h3 = role_config["higher_is_better"]

    # Invert sign if lower metric is superior (e.g. goals conceded for GK)
    sign1 = "+" if h1 else "-"
    sign2 = "+" if h2 else "-"
    sign3 = "+" if h3 else "-"

    query = f"""
    WITH club_baseline AS (
        SELECT 
            AVG({m1}) AS avg_m1,
            AVG({m2}) AS avg_m2,
            AVG({m3}) AS avg_m3,
            COUNT(*) AS qualified_players
        FROM fct_player_stats
        WHERE team_name ILIKE $target_club
          AND position = '{pos}'
    ),

    candidates AS (
        SELECT 
            player_id,
            player_name,
            team_name,
            league_name,
            age,
            match_rating,
            minutes_played,
            appearances,
            total_goals,
            total_assists,
            total_passes,
            total_tackles,
            total_interceptions,
            total_yellow_cards,
            total_red_cards,
            {m1} AS metric_1,
            {m2} AS metric_2,
            {m3} AS metric_3
        FROM fct_player_stats
        WHERE position = '{pos}'
          AND team_name NOT ILIKE $target_club
          AND ($feeder_league = 'All' OR league_name ILIKE $feeder_league)
          AND ($min_age IS NULL OR age >= $min_age)
          AND ($max_age IS NULL OR age <= $max_age)
    )

    SELECT 
        c.player_id,
        c.player_name,
        c.team_name AS current_club,
        c.league_name,
        c.age,
        c.match_rating,
        c.minutes_played,
        c.appearances,
        c.total_goals,
        c.total_assists,
        c.total_passes,
        c.total_tackles,
        c.total_interceptions,
        c.total_yellow_cards,
        c.total_red_cards,
        
        -- Individual Metrics & Deltas
        c.metric_1,
        ROUND(c.metric_1 - COALESCE(b.avg_m1, 0), 2) AS delta_m1,
        c.metric_2,
        ROUND(c.metric_2 - COALESCE(b.avg_m2, 0), 2) AS delta_m2,
        c.metric_3,
        ROUND(c.metric_3 - COALESCE(b.avg_m3, 0), 2) AS delta_m3,

        -- Composite Weighted Score
        ROUND(
            (
                {w1} * {sign1}((c.metric_1 - b.avg_m1) / NULLIF(b.avg_m1, 0)) +
                {w2} * {sign2}((c.metric_2 - b.avg_m2) / NULLIF(b.avg_m2, 0)) +
                {w3} * {sign3}((c.metric_3 - b.avg_m3) / NULLIF(b.avg_m3, 0))
            ) * 100.0,
            2
        ) AS composite_upgrade_score

    FROM candidates c
    CROSS JOIN club_baseline b
    WHERE (
        {sign1}(c.metric_1 - COALESCE(b.avg_m1, 0)) > 0 OR
        {sign2}(c.metric_2 - COALESCE(b.avg_m2, 0)) > 0
    )
    ORDER BY composite_upgrade_score DESC
    LIMIT $limit;
    """

    league_param = "All" if feeder_league.strip().lower() == "all" else f"%{feeder_league}%"

    result = con.execute(query, {
        "target_club": f"%{target_club}%",
        "feeder_league": league_param,
        "min_age": min_age,
        "max_age": max_age,
        "limit": limit
    }).fetchdf()

    baseline_stats = con.execute(f"""
        SELECT 
            ROUND(AVG({m1}), 2) as b_m1,
            ROUND(AVG({m2}), 2) as b_m2,
            ROUND(AVG({m3}), 2) as b_m3,
            COUNT(*) as sample_count
        FROM fct_player_stats
        WHERE team_name ILIKE $target_club AND position = '{pos}';
    """, {"target_club": f"%{target_club}%"}).fetchone()

    return result, baseline_stats, (m1, m2, m3)


if __name__ == "__main__":
    con = connectDuckDB()
    playerModel(con)

    target_club = "Manchester United"
    sub_role = "Destroyer"
    feeder = "All"
    limit = 10

    #Fetch Candidates & Baseline
    df, base, metrics = scoutingShortlist(
        con=con,
        target_club=target_club,
        feeder_league=feeder,
        sub_role=sub_role,
        min_age=20,
        max_age=28,
        limit=limit
    )

    m1, m2, m3 = metrics
    b_m1, b_m2, b_m3, sample_count = base

    #Query the actual club players who set the baseline
    pos = ROLE_METRIC_MAP[sub_role]["position"]
    club_players = con.execute(f"""
        SELECT 
            player_name, 
            age, 
            minutes_played,
            {m1}, 
            {m2}, 
            {m3}
        FROM fct_player_stats 
        WHERE team_name ILIKE $target_club AND position = '{pos}'
        ORDER BY minutes_played DESC;
    """, {"target_club": f"%{target_club}%"}).fetchdf()

    #Print Target Club Midfield Baseline Breakdown
    print("\n" + "=" * 95)
    print(f" BASELINE SQUAD: {target_club.upper()} ({pos}s, >= 450 mins)")
    print("=" * 95)
    club_players.index = range(1, len(club_players) + 1)
    print(club_players.to_string())
    print("-" * 95)
    print(f"Club Average Baseline: {m1}={b_m1} | {m2}={b_m2} | {m3}={b_m3} (Sample size: {sample_count})")
    print("=" * 95)

    #Format Candidate Display (1-indexed & with explicit role metrics)
    print(f"\nTOP {limit} SCOUTED '{sub_role.upper()}' TARGETS (Cross-League, Ages 20-28):")
    print("=" * 95)

    display_cols = [
        "player_name", "current_club", "league_name", "age", "match_rating",
        "metric_1", "delta_m1",
        "metric_2", "delta_m2",
        "metric_3", "delta_m3",
        "composite_upgrade_score"
    ]

    shortlist_view = df[display_cols].copy()
    
    # Rename columns to reflect the active role metrics cleanly
    shortlist_view.columns = [
        "Player", "Club", "League", "Age", "Match Rating",
        "Tackles/90", "Tackles v baseline",
        "Ints/90", "Ints v baseline",
        "Fouls/90", "Fouls v baseline",
        "Score"
    ]
    
    # Set index to start from 1 instead of 0
    shortlist_view.index = range(1, len(shortlist_view) + 1)
    
    print(shortlist_view.to_string())
    print("=" * 95 + "\n")