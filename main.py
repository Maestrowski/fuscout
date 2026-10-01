import questionary
from src.transform import connectDuckDB, playerModel, scoutingShortlist
from src.cli import (
    run_scouting_wizard,
    display_shortlist,
    inspect_player_details,
    POSITION_SUBROLES,
    safe_prompt,
    EXIT_CHOICE
)


def scout_role_flow(con, target_club, feeder_league, min_age, max_age, sub_role):
    """Executes the query and renders shortlist + dossier navigation."""
    df, baseline, metrics = scoutingShortlist(
        con=con,
        target_club=target_club,
        feeder_league=feeder_league,
        sub_role=sub_role,
        min_age=min_age,
        max_age=max_age,
        limit=10
    )

    display_shortlist(con, df, baseline, metrics, target_club, sub_role)

    if not df.empty:
        return inspect_player_details(df)
    else:
        ans = safe_prompt(
            questionary.select,
            "No results found. What would you like to do?",
            choices=["Scout another position / role", "Start a new search from beginning", EXIT_CHOICE]
        )
        return "change_role" if ans == "Scout another position / role" else "new_search"


def pick_new_role():
    """Quick prompt to change position/role without re-entering club and league."""
    pos = safe_prompt(
        questionary.select,
        "Select position to recruit:",
        choices=list(POSITION_SUBROLES.keys()) + [EXIT_CHOICE]
    )
    sub_role = safe_prompt(
        questionary.select,
        f"Select tactical sub-role ({pos}):",
        choices=POSITION_SUBROLES[pos] + [EXIT_CHOICE]
    )
    return sub_role


def main():
    con = connectDuckDB()
    playerModel(con)

    while True:
        target_club, feeder_league, min_age, max_age, sub_role, position = run_scouting_wizard(con)

        while True:
            action = scout_role_flow(con, target_club, feeder_league, min_age, max_age, sub_role)

            if action == "change_role":
                sub_role = pick_new_role()
                continue
            elif action == "new_search":
                break


if __name__ == "__main__":
    main()