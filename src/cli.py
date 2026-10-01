import sys
import questionary
from tabulate import tabulate
import pandas as pd
from src.transform import (
    ROLE_METRIC_MAP,
    getAvailableLeagues,
    getAvailableClubs,
    getClubSquadMembers,
    scoutingShortlist
)

BACK_CHOICE = "<-- Go Back"
EXIT_CHOICE = "Exit / Quit"

POSITION_SUBROLES = {
    "Attacker": [
        "Inside Forward",
        "Poacher",
        "Target Man",
        "False Nine",
        "Center Forward",
        "Winger"
    ],
    "Midfielder": [
        "Box-to-Box",
        "Destroyer",
        "Deep Lying Playmaker",
        "Advanced Playmaker",
        "Shadow Striker"
    ],
    "Defender": [
        "Ball playing center back",
        "Stopper",
        "Attacking full back",
        "Defensive full back",
        "Wing back"
    ],
    "Goalkeeper": [
        "Goalkeeper"
    ]
}


def safe_prompt(prompt_func, *args, **kwargs):
    """Executes a questionary prompt. Exits cleanly on None (Ctrl+C) or EXIT_CHOICE."""
    try:
        val = prompt_func(*args, **kwargs).ask()
    except KeyboardInterrupt:
        val = None

    if val is None or val == EXIT_CHOICE:
        print("\n\n[•] Scouting session ended. Goodbye!\n")
        sys.exit(0)
    return val


def run_scouting_wizard(con):
    """
    Step machine supporting backward navigation (<-- Go Back)
    and clean menu-driven exit.
    """
    step = 1
    state = {
        "target_league": None,
        "target_club": None,
        "feeder_league": "All",
        "min_age": None,
        "max_age": None,
        "position": None,
        "sub_role": None
    }

    leagues = getAvailableLeagues()

    while step <= 6:
        # Step 1: Domestic League
        if step == 1:
            print("\n" + "=" * 80)
            print("                FOOTBALL INTELLIGENCE SCOUTING SYSTEM")
            print("=" * 80)
            choices = leagues + [EXIT_CHOICE]
            ans = safe_prompt(
                questionary.select,
                "Select your club's domestic league:",
                choices=choices
            )
            state["target_league"] = ans
            step += 1

        # Step 2: Club
        elif step == 2:
            clubs = getAvailableClubs(con, state["target_league"])
            choices = [BACK_CHOICE] + clubs + [EXIT_CHOICE]
            ans = safe_prompt(
                questionary.select,
                f"Select your club ({state['target_league']}):",
                choices=choices
            )
            if ans == BACK_CHOICE:
                step -= 1
                continue
            state["target_club"] = ans
            step += 1

        # Step 3: Feeder League Scope
        elif step == 3:
            choices = [
                "Scout all Top 5 leagues (Default)",
                "Filter to a specific league",
                BACK_CHOICE,
                EXIT_CHOICE
            ]
            ans = safe_prompt(
                questionary.select,
                "Select scouting feeder pool:",
                choices=choices
            )
            if ans == BACK_CHOICE:
                step -= 1
                continue
            elif ans == "Filter to a specific league":
                feeder_ans = safe_prompt(
                    questionary.select,
                    "Select target feeder league:",
                    choices=[BACK_CHOICE] + leagues + [EXIT_CHOICE]
                )
                if feeder_ans == BACK_CHOICE:
                    continue
                state["feeder_league"] = feeder_ans
            else:
                state["feeder_league"] = "All"
            step += 1

        # Step 4: Age Filters
        elif step == 4:
            print("\n[i] Enter age bounds (or leave empty for any). Type 'b' to go back.")
            min_raw = safe_prompt(
                questionary.text,
                "Minimum player age (default: any):"
            ).strip()

            if min_raw.lower() == 'b':
                step -= 1
                continue

            max_raw = safe_prompt(
                questionary.text,
                "Maximum player age (default: any):"
            ).strip()

            if max_raw.lower() == 'b':
                continue

            state["min_age"] = int(min_raw) if min_raw.isdigit() else None
            state["max_age"] = int(max_raw) if max_raw.isdigit() else None
            step += 1

        # Step 5: Position
        elif step == 5:
            choices = [BACK_CHOICE] + list(POSITION_SUBROLES.keys()) + [EXIT_CHOICE]
            ans = safe_prompt(
                questionary.select,
                "Select position to recruit:",
                choices=choices
            )
            if ans == BACK_CHOICE:
                step -= 1
                continue
            state["position"] = ans
            step += 1

        # Step 6: Tactical Sub-role
        elif step == 6:
            pos_roles = POSITION_SUBROLES[state["position"]]
            choices = [BACK_CHOICE] + pos_roles + [EXIT_CHOICE]
            ans = safe_prompt(
                questionary.select,
                f"Select tactical sub-role ({state['position']}):",
                choices=choices
            )
            if ans == BACK_CHOICE:
                step -= 1
                continue
            state["sub_role"] = ans
            step += 1

    return (
        state["target_club"],
        state["feeder_league"],
        state["min_age"],
        state["max_age"],
        state["sub_role"],
        state["position"]
    )


def display_shortlist(con, df, baseline_stats, metrics, target_club, sub_role):
    m1, m2, m3 = metrics
    b_m1, b_m2, b_m3, sample_count = baseline_stats
    pos = ROLE_METRIC_MAP[sub_role]["position"]

    def format_lbl(m):
        return m.replace("_per_90", "/90").replace("_", " ").title()

    l1, l2, l3 = format_lbl(m1), format_lbl(m2), format_lbl(m3)

    # 1. Current Club Baseline Squad
    club_squad = getClubSquadMembers(con, target_club, pos, metrics)
    print("\n" + "=" * 105)
    print(f" CURRENT SQUAD CONTEXT: {target_club.upper()} ({pos}s, >= 450 mins)")
    print("=" * 105)

    if not club_squad.empty:
        squad_rows = []
        for i, r in club_squad.iterrows():
            squad_rows.append([
                i + 1,
                r["player_name"],
                r["age"],
                int(r["minutes_played"]),
                f"{r['match_rating']:.2f}",
                f"{r['metric_1']:.2f}",
                f"{r['metric_2']:.2f}",
                f"{r['metric_3']:.2f}"
            ])
        print(tabulate(
            squad_rows,
            headers=["#", "Player", "Age", "Mins", "Rating", l1, l2, l3],
            tablefmt="github"
        ))
    else:
        print(f" [!] No {pos}s recorded >= 450 minutes for {target_club}.")

    print("-" * 105)
    print(f" Club Average Baseline: {l1}: {b_m1:.2f} | {l2}: {b_m2:.2f} | {l3}: {b_m3:.2f} (Sample: {sample_count} players)")
    print("=" * 105)

    # 2. Top 10 Shortlist
    print(f"\n TOP 10 RECRUITMENT TARGETS: {sub_role.upper()} ({pos})")
    print("=" * 105)

    if df.empty:
        print(f"\n [!] No candidate targets found matching these criteria.\n")
        return

    display_rows = []
    for idx, row in df.iterrows():
        display_rows.append([
            idx + 1,
            row["player_name"],
            row["current_club"],
            row["league_name"],
            row["age"],
            f"{row['match_rating']:.2f}",
            f"{row['metric_1']:.2f}",
            f"{row['delta_m1']:+.2f}",
            f"{row['metric_2']:.2f}",
            f"{row['delta_m2']:+.2f}",
            f"{row['metric_3']:.2f}",
            f"{row['delta_m3']:+.2f}",
            f"{row['composite_upgrade_score']:+.2f}"
        ])

    headers = [
        "#", "Player", "Club", "League", "Age", "Rating",
        l1, "Δ", l2, "Δ", l3, "Δ", "Score"
    ]

    print(tabulate(display_rows, headers=headers, tablefmt="github"))
    print("=" * 105 + "\n")


def inspect_player_details(df):
    """Provides navigation between dossiers, role changes, new searches, or exit."""
    while True:
        choices = [
            f"{i+1}. {row['player_name']} ({row['current_club']}) - Score: {row['composite_upgrade_score']:+.2f}"
            for i, row in df.iterrows()
        ]
        choices.append("Scout another position / role")
        choices.append("Start a new search from beginning")
        choices.append(EXIT_CHOICE)

        selection = safe_prompt(
            questionary.select,
            "Select a player to view dossier, change role, or exit:",
            choices=choices
        )

        if selection == "Scout another position / role":
            return "change_role"
        elif selection == "Start a new search from beginning":
            return "new_search"

        idx = int(selection.split(".")[0]) - 1
        p = df.iloc[idx]

        print("\n" + "#" * 60)
        print(f"       PLAYER DOSSIER: {p['player_name'].upper()}")
        print("#" * 60)
        print(f" Club:              {p['current_club']}")
        print(f" League:            {p['league_name']}")
        print(f" Age:               {p['age']}")
        print(f" Minutes Played:    {int(p['minutes_played'])} ({int(p['appearances'])} apps)")
        print(f" Overall Rating:    {p['match_rating']:.2f}")
        print("-" * 60)
        print(" [•] ATTACKING & CREATIVE OUTPUT")
        print(f"     Goals:             {int(p['total_goals'])}")
        print(f"     Assists:           {int(p['total_assists'])}")
        print(f"     Total Passes:      {int(p['total_passes'])}")
        print("-" * 60)
        print(" [•] DEFENSIVE & DISCIPLINARY")
        print(f"     Tackles:           {int(p['total_tackles'])}")
        print(f"     Interceptions:     {int(p['total_interceptions'])}")
        print(f"     Yellow Cards:      {int(p['total_yellow_cards'])}")
        print(f"     Red Cards:         {int(p['total_red_cards'])}")
        print("#" * 60 + "\n")

        post_dossier_action = safe_prompt(
            questionary.select,
            "Action:",
            choices=[
                "Return to Player Shortlist",
                "Scout another position / role",
                "Start a new search from beginning",
                EXIT_CHOICE
            ]
        )

        if post_dossier_action == "Return to Player Shortlist":
            continue
        elif post_dossier_action == "Scout another position / role":
            return "change_role"
        elif post_dossier_action == "Start a new search from beginning":
            return "new_search"