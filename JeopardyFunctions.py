import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import os
from joblib import load
import psycopg2

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
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    search_destination_sql_dict = {
        "Clue": "clue",
        "Category": "category",
        "Correct Response": "correct_response",
    }

    clues_columns = [
        "Air Date",
        "Round",
        "Clue Value",
        "Category",
        "Clue",
        "Number Correct",
        "Correct Response",
    ]

    search_destination_sql = search_destination_sql_dict[search_destination]
    if exact == "Contains":
        query_clues = """
        SELECT air_date, round_id round, clue_value, category, clue, n_correct, correct_response
        FROM clues_view
        WHERE {search_destination_sql} ILIKE '%{term}%'
        ORDER BY air_date desc
        """.format(
            search_destination_sql=search_destination_sql, term=term
        )
        cur.execute(query_clues)
        results = cur.fetchall()
        clues = pd.DataFrame(results, columns=clues_columns)
        return clues
    else:
        query_clues = """
        SELECT air_date, round_id round, clue_value, category, clue, n_correct, correct_response
        FROM clues_view
        WHERE {search_destination_sql} ILIKE '{term}'
        ORDER BY air_date desc
        """.format(
            search_destination_sql=search_destination_sql, term=term
        )
        cur.execute(query_clues)
        results = cur.fetchall()
        clues = pd.DataFrame(results, columns=clues_columns)
        return clues

    cur.close()
    conn.close()


def game_progression_win_probability(show_number):
    """
    Inputs: Show number

    Output: NumPy array of the progression of the Jeopardy game at the end of every clue. Columns include the show number, the clue number, the score of each contestant,
    the remaining value of clues on the board, and the remaining number of daily doubles.
    """

    conn = psycopg2.connect(database_url)
    cur_game = conn.cursor()
    query = f"""SELECT round_id, CAST(order_number as int), is_dd, clue_value, value, correct_contestants, incorrect_contestants
        FROM clues_view 
        where show_number = '{show_number}' and round_id in ('J', 'DJ') ORDER BY round_id desc, order_number asc"""

    cur_game.execute(query)
    results = cur_game.fetchall()
    game = pd.DataFrame(
        results,
        columns=[
            "round_id",
            "order_number",
            "is_dd",
            "clue_value",
            "value",
            "correct_contestants",
            "incorrect_contestants",
        ],
    )

    cur_nicknames = conn.cursor()
    query_nicks = f""" SELECT contestant_1_nickname, contestant_2_nickname, returning_champion_nickname from games_view where show_number = {show_number}"""
    cur_nicknames.execute(query_nicks)
    nickname_results = cur_nicknames.fetchall()
    name_data = pd.DataFrame(
        nickname_results, columns=["contestant_1", "contestant_2", "returning_champion"]
    ).melt()
    cur_game.close()
    cur_nicknames.close()
    conn.close()
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

    game["value"] = (
        game["value"]
        .str.split("$")
        .str[1]
        .replace("[\$,]", "", regex=True)
        .astype(float)
    )

    starting_state = np.array([show_number, 0, 3, 54000, 0, 0, 0])  # , 0,0,0,0,0,0
    contestant_1_score = 0
    contestant_2_score = 0
    returning_champion_score = 0

    remaining_value = 54000
    remaining_dds = 3
    question_number = 0

    for index, row in game.iterrows():
        if "contestant_1" in row["correct_contestants"]:
            contestant_1_score += row["value"]
        if "contestant_2" in row["correct_contestants"]:
            contestant_2_score += row["value"]
        if "returning_champion" in row["correct_contestants"]:
            returning_champion_score += row["value"]

        if "contestant_1" in row["incorrect_contestants"]:
            contestant_1_score -= row["value"]
        if "contestant_2" in row["incorrect_contestants"]:
            contestant_2_score -= row["value"]
        if "returning_champion" in row["incorrect_contestants"]:
            returning_champion_score -= row["value"]

        remaining_value -= row["clue_value"]

        if row["is_dd"] == True:
            remaining_dds -= 1
        question_number += 1

        next_question = np.array(
            [
                show_number,
                question_number,
                remaining_dds,
                remaining_value,
                contestant_1_score,
                contestant_2_score,
                returning_champion_score,
            ]
        )

        starting_state = np.vstack((starting_state, next_question))

    return pd.DataFrame(
        starting_state,
        columns=[
            "show_number",
            "question_number",
            "remaining_dds",
            "remaining_value",
            "contestant_1_score",
            "contestant_2_score",
            "returning_champion_score",
        ],
    )


def predict_game_outcome(s1, s2, s3):
    data = pd.Series(
        data=[s1, s2, s3], index=["Contestant 1", "Contestant 2", "Returning Champion"]
    ).sort_values(ascending=False)
    data[data <= 0] = 1

    first_state = return_state(data.iloc[0], data.iloc[1])
    second_state = return_state(data.iloc[1], data.iloc[2])

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    query = f"""SELECT "First Place" , "Second Place" , "Third Place" FROM  win_probability_table where first_state = '{first_state}' and second_state = '{second_state}'"""
    cur.execute(query)
    results = cur.fetchall()
    probabilities = pd.DataFrame(
        results, columns=["First Place", "Second Place", "Third Place"]
    ).T

    conn.close()
    cur.close()

    probabilities.index = data.index
    probabilities = probabilities.squeeze()

    return probabilities


def is_locked(s1, s2, s3, rv, rdds):
    scores = [s1, s2, s3]
    scores.sort()
    a, b = scores[-1], scores[-2]
    if a > ((b + rv) * 2 ** (1 + rdds)):
        return 1
    else:
        return 0


def return_state(score_1, score_2):
    score_ratio = score_2 / score_1
    if score_ratio == 1:
        return "Tied"
    elif score_ratio < 0.5:
        return "Locked"
    elif score_ratio == 0.5:
        return "Lock Tie"
    elif (score_ratio > 0.5) & (score_ratio < (2 / 3)):
        return "Crush"
    elif (score_ratio >= (2 / 3)) & (score_ratio < (3 / 4)):
        return "Two Thirds"
    elif (score_ratio >= (3 / 4)) & (score_ratio < (4 / 5)):
        return "Three Fourths"
    else:
        return "Four Fifths"


def fj_result(show_number):
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    query = f"""SELECT COUNT(order_number) + 1 "question_number", 0 "remaining_value", contestant_1_score, contestant_2_score, returning_champion_score 
    FROM games_view g
    LEFT JOIN clues_view c using(show_number)
    where regular_season = true and g.show_number = {show_number} and c.order_number not in ('FJ', 'TB') and winning_contestant <> 'Tied'
    GROUP BY  g.show_number, contestant_1_score, contestant_2_score, returning_champion_score, winning_contestant 
        """
    cur.execute(query)
    results = cur.fetchall()
    final = pd.DataFrame(
        results,
        columns=[
            "question_number",
            "remaining_value",
            "contestant_1_score",
            "contestant_2_score",
            "returning_champion_score",
        ],
    )
    cur.close()
    conn.close()

    final.reset_index(drop=True, inplace=True)
    scores = pd.Series(
        [
            final["contestant_1_score"].iloc[0],
            final["contestant_2_score"].iloc[0],
            final["returning_champion_score"].iloc[0],
        ],
        index=["contestant_1", "contestant_2", "returning_champion"],
    )
    scores = pd.DataFrame(scores.apply(lambda x: 1 if x == scores.max() else 0)).T

    return pd.concat([final, scores], axis=1, ignore_index=False)


def final_model_plot_data(show_number):
    game_data = final_model(show_number)
    episode_end = fj_result(show_number)
    return_data = pd.concat([game_data, episode_end])

    return_data["is_dd"] = (
        return_data["remaining_dds"].shift() - return_data["remaining_dds"]
    )

    return return_data


def final_model(show_number):
    lr = load("JeopardyDashboard/logistic_regression.joblib")

    dff = game_progression_win_probability(show_number)
    dff["is_locked"] = dff.apply(
        lambda x: is_locked(
            x["contestant_1_score"],
            x["contestant_2_score"],
            x["returning_champion_score"],
            x["remaining_value"],
            x["remaining_dds"],
        ),
        axis=1,
    )

    final_predictions = pd.DataFrame()
    for row in dff.itertuples():
        if row.is_locked == 1:
            scores = pd.Series(
                [
                    row.contestant_1_score,
                    row.contestant_2_score,
                    row.returning_champion_score,
                ],
                index=["contestant_1", "contestant_2", "returning_champion"],
            )
            scores = scores.apply(lambda x: 1 if x == scores.max() else 0)
            predictions = pd.DataFrame(scores).T
        elif row.question_number == dff["question_number"].max():
            predictions = (
                pd.DataFrame(
                    predict_game_outcome(
                        row.contestant_1_score,
                        row.contestant_2_score,
                        row.returning_champion_score,
                    )
                )
                .sort_index()
                .T
            )
            predictions.columns = ["contestant_1", "contestant_2", "returning_champion"]
        else:
            scores_array = np.array(
                [
                    [
                        row.contestant_1_score,
                        row.contestant_2_score,
                        row.returning_champion_score,
                        row.remaining_value,
                    ]
                ]
            )
            predictions = pd.DataFrame(lr.predict_proba(scores_array))
            predictions.columns = ["contestant_1", "contestant_2", "returning_champion"]
        final_predictions = pd.concat([final_predictions, predictions])

    final_predictions = final_predictions.reset_index().drop(["index"], axis=1)
    dff.reset_index(inplace=True, drop=True)
    return_data_test = dff.merge(final_predictions, left_index=True, right_index=True)
    return return_data_test
