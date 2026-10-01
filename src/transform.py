import duckdb
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"

def connectDuckDB():
    return duckdb.connect()

def playerModel(con: duckdb.DuckDBPyConnection):
    # 1. Ingest raw JSON data
    # DuckDB auto-detects schema and unpacks JSON
    raw_files_pattern = str(RAW_DATA_DIR / "*.json").replace("\\", "/")
    
    con.execute(f"""
        CREATE OR REPLACE VIEW stg_raw_players AS 
        SELECT * FROM read_json_auto('{raw_files_pattern}');
    """)

    # 2. Data preprocessing and transformation
    con.execute("""
        CREATE OR REPLACE TABLE fct_player_stats AS 
        SELECT 
            CAST(player.id AS BIGINT) AS player_id,
            CAST(player.name AS VARCHAR) AS player_name,
            CAST(COALESCE(player.age, 0) AS INTEGER) AS age,
            CAST(statistics[1].team.name AS VARCHAR) AS team_name,
            CAST(statistics[1].league.name AS VARCHAR) AS league_name,
            CAST(COALESCE(statistics[1].games.position, 'Unknown') AS VARCHAR) AS position,
            CAST(COALESCE(statistics[1].games.minutes, 0) AS INTEGER) AS minutes_played,
            CAST(COALESCE(statistics[1].tackles.total, 0) AS INTEGER) AS total_tackles,
            CAST(COALESCE(statistics[1].tackles.interceptions, 0) AS INTEGER) AS total_interceptions,
            
            -- Derived Per-90 Defensive Metrics
            ROUND(
                (CAST(COALESCE(statistics[1].tackles.total, 0) AS FLOAT) / 
                 NULLIF(statistics[1].games.minutes, 0)) * 90.0, 
                2
            ) AS tackles_per_90,
            
            ROUND(
                (CAST(COALESCE(statistics[1].tackles.interceptions, 0) AS FLOAT) / 
                 NULLIF(statistics[1].games.minutes, 0)) * 90.0, 
                2
            ) AS interceptions_per_90
            
        FROM stg_raw_players
        WHERE statistics[1].games.minutes IS NOT NULL
          AND statistics[1].games.minutes >= 450; -- Filter out small-sample-size noise
    """)

# Calculate the squad baseline for selected club and find players that statistically outperform current squad members in the same position.
def scoutingShortlist(con: duckdb.DuckDBPyConnection, target_club: str, feeder_league: str, limit: int = 5):
    """
    Calculates the squad baseline for target_club and queries candidate upgrades
    from feeder_league using Common Table Expressions (CTEs).
    """
    query = """
    WITH club_baseline AS (
        -- Calculate the target club's midfield average defensive output
        SELECT 
            AVG(tackles_per_90) AS avg_tackles,
            AVG(interceptions_per_90) AS avg_interceptions,
            COUNT(*) AS qualified_players
        FROM fct_player_stats
        WHERE team_name ILIKE $target_club
          AND position = 'Midfielder'
    ),
    
    candidates AS (
        -- Select eligible midfielders from the candidate league
        SELECT 
            player_id,
            player_name,
            team_name,
            league_name,
            age,
            minutes_played,
            tackles_per_90,
            interceptions_per_90
        FROM fct_player_stats
        WHERE league_name ILIKE $feeder_league
          AND position = 'Midfielder'
    )
    
    -- Filter candidates who represent a statistical upgrade over target club's baseline
    SELECT 
        c.player_name,
        c.team_name AS current_club,
        c.age,
        c.minutes_played,
        c.tackles_per_90,
        ROUND(c.tackles_per_90 - COALESCE(b.avg_tackles, 0), 2) AS tackle_delta,
        c.interceptions_per_90,
        ROUND(c.interceptions_per_90 - COALESCE(b.avg_interceptions, 0), 2) AS int_delta,
        ROUND(
            (c.tackles_per_90 - COALESCE(b.avg_tackles, 0)) + 
            (c.interceptions_per_90 - COALESCE(b.avg_interceptions, 0)), 
            2
        ) AS composite_upgrade_score
    FROM candidates c
    CROSS JOIN club_baseline b
    WHERE c.tackles_per_90 > COALESCE(b.avg_tackles, 0)
       OR c.interceptions_per_90 > COALESCE(b.avg_interceptions, 0)
    ORDER BY composite_upgrade_score DESC
    LIMIT $limit;
    """
    
    # Prevent SQL injection
    result = con.execute(
        query, 
        {"target_club": f"%{target_club}%", "feeder_league": f"%{feeder_league}%", "limit": limit}
    ).fetchdf()
    
    # Baseline statistics for display
    baseline_stats = con.execute("""
        SELECT 
            ROUND(AVG(tackles_per_90), 2) as baseline_tackles,
            ROUND(AVG(interceptions_per_90), 2) as baseline_ints,
            COUNT(*) as sample_count
        FROM fct_player_stats
        WHERE team_name ILIKE $target_club AND position = 'Midfielder';
    """, {"target_club": f"%{target_club}%"}).fetchone()

    return result, baseline_stats

if __name__ == "__main__":
    # Test execution
    con = connectDuckDB()
    playerModel(con)
    
    # Test query
    shortlist_df, baseline = scoutingShortlist(con, target_club="Manchester United", feeder_league="Bundesliga")
    print(f"\nManchester United Baseline (Tackles/90, Ints/90): {baseline}")
    print("\nTop Upgrades:")
    print(shortlist_df)