import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os

database_url = os.getenv("database_url_jeopardy")


def pivot_game(show_number):
    engine = create_engine(database_url)

    query = f"""SELECT * FROM clues_view where show_number = '{show_number}'"""

    game = pd.read_sql(query, con=engine)
    game["category"] = game["category"].str.replace('"', "'")
    fj_correct_response = game[(game["round_id"] == "FJ")][
        ["category", "clue_value", "clue", "correct_response"]
    ].pivot(columns="category", index="clue_value", values="correct_response")
    fj_clue = game[(game["round_id"] == "FJ")][
        ["category", "clue_value", "clue"]
    ].pivot(columns="category", index="clue_value", values="clue")
    game = game[(game["clue_value"] != "FJ") & (game["clue_value"] != "TB")]
    game["clue_value"] = game["clue_value"].astype(float)

    j_round_cat_order = (
        game[game["round_id"] == "J"][["category_column", "category"]]
        .drop_duplicates()["category"]
        .to_list()
    )
    dj_round_cat_order = (
        game[game["round_id"] == "DJ"][["category_column", "category"]]
        .drop_duplicates()["category"]
        .to_list()
    )

    df_j_clues = (
        game[(game["round_id"] == "J")][["category", "clue_value", "clue"]]
        .pivot(columns="category", index="clue_value", values="clue")
        .reset_index()
        .fillna("")
    )

    df_j_clues = df_j_clues[j_round_cat_order]

    df_j_correct_response = (
        game[(game["round_id"] == "J")][
            ["category", "clue_value", "clue", "correct_response"]
        ]
        .pivot(columns="category", index="clue_value", values="correct_response")
        .reset_index()
        .fillna("")
    )
    df_j_correct_response = df_j_correct_response[j_round_cat_order]

    df_dj_clues = (
        game[(game["round_id"] == "DJ")][["category", "clue_value", "clue"]]
        .pivot(columns="category", index="clue_value", values="clue")
        .reset_index()
        .fillna("")
    )
    df_dj_clues = df_dj_clues[dj_round_cat_order]

    df_dj_correct_response = (
        game[(game["round_id"] == "DJ")][
            ["category", "clue_value", "clue", "correct_response"]
        ]
        .pivot(columns="category", index="clue_value", values="correct_response")
        .reset_index()
        .fillna("")
    )
    df_dj_correct_response = df_dj_correct_response[dj_round_cat_order]

    engine.dispose()
    return (
        df_j_clues,
        df_j_correct_response,
        df_dj_clues,
        df_dj_correct_response,
        fj_clue,
        fj_correct_response,
    )



def game_progression(show_number):
    engine = create_engine(database_url)
    query = f"""SELECT round_id, CAST(order_number as int), is_dd, clue_value,  correct_contestants, incorrect_contestants
    FROM clues_view 
    where show_number = '{show_number}' and round_id in ('J', 'DJ') ORDER BY round_id desc, order_number asc"""

    game = pd.read_sql(query, con=engine)

    query_nicks = f""" SELECT contestant_1_nickname, contestant_2_nickname, returning_champion_nickname from games_view where show_number = {show_number}"""
    name_data = pd.read_sql(query_nicks, con=engine).melt()
    name_data["variable"] = name_data["variable"].str.split("_n").str[0]
    name_data["first_name"] = name_data["value"].str.split(" ").str[0]
    rename_dict = dict(zip(name_data["first_name"], name_data["variable"]))

    game.loc[:, "correct_contestants"] = (
        game["correct_contestants"].replace(rename_dict, regex=True).replace(np.NaN, "")
    )
    game.loc[:, "incorrect_contestants"] = (
        game["incorrect_contestants"]
        .replace(rename_dict, regex=True)
        .replace(np.NaN, "")
    )

    starting_state = np.array([0, 0, 0, 0])
    contestant_1_score = 0
    contestant_2_score = 0
    returning_champion_score = 0

    question_number = 0

    contestant_1_correct = 0
    contestant_2_correct = 0
    returning_champion_correct = 0

    contestant_1_incorrect = 0
    contestant_2_incorrect = 0
    returning_champion_incorrect = 0

    for index, row in game.iterrows():
        if "contestant_1" in row["correct_contestants"]:
            contestant_1_score += row["clue_value"]
            contestant_1_correct += 1
        if "contestant_2" in row["correct_contestants"]:
            contestant_2_score += row["clue_value"]
            contestant_2_correct += 1
        if "returning_champion" in row["correct_contestants"]:
            returning_champion_score += row["clue_value"]
            returning_champion_correct += 1

        if "contestant_1" in row["incorrect_contestants"]:
            contestant_1_score -= row["clue_value"]
            contestant_1_incorrect += 1
        if "contestant_2" in row["incorrect_contestants"]:
            contestant_2_score -= row["clue_value"]
            contestant_2_incorrect += 1
        if "returning_champion" in row["incorrect_contestants"]:
            returning_champion_score -= row["clue_value"]
            returning_champion_incorrect += 1

        question_number += 1

        next_question = np.array(
            [
                question_number,
                contestant_1_score,
                contestant_2_score,
                returning_champion_score,
            ]
        )

        starting_state = np.vstack((starting_state, next_question))

    players = list(rename_dict.keys())
    df = pd.DataFrame(starting_state)

    daily_doubles = game["is_dd"].to_numpy()
    daily_doubles = pd.Series(np.insert(daily_doubles, 0, False)).replace(
        [True, False], [1, 0]
    )
    df = pd.concat([df, daily_doubles], axis=1)
    df.columns = ["Question Number", players[0], players[1], players[2], "Daily Double"]

    query_final = f"""SELECT contestant_1_score, contestant_2_score, returning_champion_score from games_view where show_number = {show_number}"""
    final_score = pd.read_sql(query_final, con=engine).to_numpy()
    final_score = np.insert(final_score, 0, df["Question Number"].max() + 1)
    final_score = pd.DataFrame(np.insert(final_score, 4, 0)).transpose()
    final_score.columns = df.columns
    df = pd.concat([df, final_score], axis=0).reset_index().drop(["index"], axis=1)

    engine.dispose()
    return (
        df,
        [contestant_1_correct, contestant_2_correct, returning_champion_correct],
        [contestant_1_incorrect, contestant_2_incorrect, returning_champion_incorrect],
    )


def find_data(search_destination, term, exact="Contains"):
    engine = create_engine(database_url)
    search_destination_sql_dict = {
        "Clue": "clue",
        "Category": "category",
        "Correct Response": "correct_response",
    }
    search_destination_sql = search_destination_sql_dict[search_destination]
    if exact == "Contains":
        query_clues = f"""
        SELECT air_date, round_id round, clue_value, category, clue, n_correct, correct_response
        FROM clues_view
        WHERE {search_destination_sql} ILIKE '%%{term}%%' or {search_destination_sql} ILIKE '{term}%%' or {search_destination_sql} ILIKE '%%{term}'
        ORDER BY air_date desc
        """
        clues = pd.read_sql(query_clues, con=engine)
        clues.columns = [
            "Air Date",
            "Round",
            "Clue Value",
            "Category",
            "Clue",
            "Number Correct",
            "Correct Response",
        ]
        engine.dispose()
        return clues
    else:
        query_clues = f"""
        SELECT air_date, round_id round, clue_value, category, clue, n_correct, correct_response
        FROM clues_view
        WHERE {search_destination_sql} ILIKE '{term}'
        ORDER BY air_date desc
        """
        clues = pd.read_sql(query_clues, con=engine)
        clues.columns = [
            "Air Date",
            "Round",
            "Clue Value",
            "Category",
            "Clue",
            "Number Correct",
            "Correct Response",
        ]
        engine.dispose()
        return clues
