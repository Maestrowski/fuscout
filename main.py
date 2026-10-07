import questionary
from src.transform import (
    connectDuckDB,
    playerModel,
    scoutingShortlist,
    findSimilarPlayers
)
from src.cli import (
    run_scouting_wizard,
    display_shortlist,
    inspect_player_details,
    select_target_club,
    choose_scouting_mode,
    select_target_player,
    prompt_search_filters,
    display_similarity_shortlist,
    POSITION_SUBROLES,
    safe_prompt,
    EXIT_CHOICE
)


def scout_role_flow(con, target_club, feeder_league, min_age, max_age, sub_role):
    """Executes the deficit query and renders shortlist + dossier navigation."""
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
        # Select Club
        target_league, target_club = select_target_club(con)

        # Choose Mode
        mode = choose_scouting_mode()

        if "Tactical Upgrade" in mode:
            # Deficit Upgrade flow
            wizard_res = run_scouting_wizard(
                con, preset_league=target_league, preset_club=target_club
            )
            if wizard_res is None:
                continue

            target_club, feeder_league, min_age, max_age, sub_role, position = wizard_res

            while True:
                action = scout_role_flow(con, target_club, feeder_league, min_age, max_age, sub_role)

                if action == "change_role":
                    sub_role = pick_new_role()
                    continue
                elif action == "new_search":
                    break

        elif "Player Profile Clone" in mode:
            # Similarity Matching flow
            while True:
                target_pid = select_target_player(con, target_club)
                if target_pid is None:
                    break

                feeder_league, min_age, max_age = prompt_search_filters()

                sim_df, target_player, metrics = findSimilarPlayers(
                    con=con,
                    target_player_id=target_pid,
                    feeder_league=feeder_league,
                    min_age=min_age,
                    max_age=max_age,
                    limit=10
                )

                display_similarity_shortlist(sim_df, target_player, metrics)

                if not sim_df.empty:
                    action = inspect_player_details(sim_df)
                    if action == "new_search":
                        break
                    continue
                else:
                    ans = safe_prompt(
                        questionary.select,
                        "No candidates found. What would you like to do?",
                        choices=["Select another squad player", "Start a new search from beginning", EXIT_CHOICE]
                    )
                    if ans == "Start a new search from beginning":
                        break


if __name__ == "__main__":
    main()