import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, Input, Output, dcc, html, register_page, callback
import plotly.graph_objects as go
import plotly.express as px
from sqlalchemy import create_engine
import os

database_url = os.getenv("database_url_jeopardy")

register_page(
    __name__,
    path="/Champions",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)

explanation_string = (
    "This dashboard allows users to select a Jeopardy champion and see some of their match statistics, such as their win streak, winnings, and average winnings. "
    "It also shows what percent of all clues in their matches were answered correctly by the champion, what percent of the champion's responses were correct, and what percent of Final Jeopardy responses were correct. "
    "Finally it plots a histogram of the contestant's winnings and win streak compared to all other champions, and displays all clues from the champion's games"
)


def serve_layout_contestants():
    return dbc.Container(
        [
            html.H1("Champions Dashboard"),
            html.P(explanation_string, style={"fontSize": 24}),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.P("Select Champion:"),
                            dcc.Dropdown(
                                id="champion-select",
                                options=[],
                                value="Ken Jennings",
                                clearable=False,
                            ),
                        ],
                        width=3,
                    ),
                ]
            ),
            html.Hr(),
            dbc.Row([dbc.Col([dcc.Graph(id="champion-indicator")])]),
            dbc.Row(
                [
                    dbc.Col([dcc.Graph(id="win-streak-hist")], width=6),
                    dbc.Col([dcc.Graph(id="winnings-hist")], width=6),
                ]
            ),
            html.Hr(),
            dbc.Row(
                [
                    html.H2(id="contestant-clues"),
                    dbc.Col(
                        id="correct-answers", width=8, style={"marginBottom": "4.5em"}
                    ),
                ]
            ),
        ],
        fluid=True,
    )


layout = serve_layout_contestants


@callback(
    Output(component_id="champion-select", component_property="options"),
    Output(component_id="win-streak-hist", component_property="figure"),
    Output(component_id="winnings-hist", component_property="figure"),
    Output(component_id="champion-indicator", component_property="figure"),
    Output(component_id="correct-answers", component_property="children"),
    Output(component_id="contestant-clues", component_property="children"),
    Input(component_id="champion-select", component_property="value"),
)
def get_champions(champion):
    engine = create_engine(database_url)

    champions_query = f"""
        SELECT contestant, max(returning_champion_streak::float), max(returning_champion_winnings), max(returning_champion_winnings::float)/max(returning_champion_streak::float) avg_winnings
        from contestants c
        INNER JOIN games_view g on c.contestant = g.returning_champion 
        WHERE regular_season = True AND returning_champion_winnings is not null
        GROUP BY contestant
        ORDER BY max(returning_champion_winnings) desc
    """

    dff = pd.read_sql_query(champions_query, con=engine)
    dff.columns = ["contestant", "streak", "winnings", "average winnings"]
    fig_streak = px.histogram(dff, x="streak")
    fig_streak.add_vline(x=dff[dff["contestant"] == champion]["streak"].iloc[0])
    fig_streak.update_layout(
        title=f"Returning Champion Winning Streaks, {champion} Selected", height=700
    )

    fig_earnings = px.histogram(dff, x="winnings")
    fig_earnings.add_vline(x=dff[dff["contestant"] == champion]["winnings"].iloc[0])
    fig_earnings.update_layout(
        title=f"Returning Champion Winnings, {champion} Selected", height=700
    )

    indicator = go.Figure()

    indicator.add_trace(
        go.Indicator(
            mode="number+delta",
            value=dff[dff["contestant"] == champion]["streak"].iloc[0],
            title={"text": "Win Streak"},
            domain={"x": [0, 0.25], "y": [0.5, 1]},
            delta={"reference": dff["streak"].median()},
        )
    )

    indicator.add_trace(
        go.Indicator(
            mode="number+delta",
            value=dff[dff["contestant"] == champion]["winnings"].iloc[0],
            title={"text": "Winnings as Champion"},
            domain={"x": [0.25, 0.5], "y": [0.5, 1]},
            delta={"reference": dff["winnings"].median()},
        )
    )
    indicator.add_trace(
        go.Indicator(
            mode="number+delta",
            value=dff[dff["contestant"] == champion]["average winnings"].iloc[0],
            title={"text": "Average Winnings"},
            domain={"x": [0.5, 0.75], "y": [0.5, 1]},
            delta={"reference": dff["average winnings"].median()},
        )
    )

    indicator.update_layout(
        title=f"{champion}'s Statistics <br><sup>and comparison to median champion</sup>",
        height=600,
        font={"size": 24},
    )

    query = f"""
        SELECT c.show_number, game_comments, c.air_date, round_id round, value, order_number, category, clue, correct_response, correct_contestants, incorrect_contestants
        FROM clues_view c
        LEFT JOIN games_view g on c.show_number = g.show_number
        where c.show_number in (select distinct show_number from contestants where contestant = '{champion}') 
        and regular_season = True
        ORDER BY c.show_number, order_number
        """

    query_nickname = f"""
        SELECT distinct contestant_nickname from contestants where contestant ='{champion}'
        """

    dff_clues = pd.read_sql_query(query, con=engine)

    dff_clues["order_number"] = (
        dff_clues["order_number"].astype(str).str.replace("FJ", "61").astype(int)
    )
    try:
        dff_clues["round"] = (
            dff_clues["round"]
            .astype("category")
            .cat.reorder_categories(["J", "DJ", "FJ"], ordered=True)
        )
    except:
        dff_clues["order_number"] = (
            dff_clues["order_number"].astype(str).str.replace("TB", "62").astype(int)
        )
        dff_clues["round"] = (
            dff_clues["round"]
            .astype("category")
            .cat.reorder_categories(["J", "DJ", "FJ", "TB"], ordered=True)
        )

    dff_clues["air_date"] = pd.DatetimeIndex(dff_clues["air_date"]).strftime("%Y-%m-%d")
    dff_clues = dff_clues.sort_values(by=["show_number", "round", "order_number"])

    table_clues = dash_table.DataTable(
        data=dff_clues.to_dict("records"),
        columns=[{"name": i, "id": i} for i in dff_clues.columns],
        style_cell={"textAlign": "left", "height": "auto"},
        page_size=15,
        style_data={"whiteSpace": "normal", "height": "auto"},
        sort_action="native",
        filter_action="native",
        export_format="csv",
    )

    nickname = pd.read_sql_query(query_nickname, con=engine).squeeze()
    engine.dispose()

    regular_clues = dff_clues[dff_clues["round"] != "FJ"]
    total = len(regular_clues)
    n_correct = regular_clues["correct_contestants"].str.contains(nickname).sum()
    n_incorrect = regular_clues["incorrect_contestants"].str.contains(nickname).sum()

    fj = dff_clues[dff_clues["round"] == "FJ"]
    n_fj_correct = fj["correct_contestants"].str.contains(nickname).sum()

    indicator.add_trace(
        go.Indicator(
            mode="number",
            value=100 * n_correct / total,
            number={"suffix": "%"},
            title={"text": "Percent of All Regular Clues Answered Correctly"},
            domain={"x": [0, 0.25], "y": [0, 0.5]},
        )
    )

    indicator.add_trace(
        go.Indicator(
            mode="number",
            value=100 * n_correct / (n_correct + n_incorrect),
            number={"suffix": "%"},
            title={"text": "Percent of Responses Being Correct"},
            domain={"x": [0.25, 0.5], "y": [0, 0.5]},
        )
    )
    indicator.add_trace(
        go.Indicator(
            mode="number",
            value=100 * n_fj_correct / len(fj),
            number={"suffix": "%"},
            title={"text": "Percent of Final Jeopardy Clues Answered Correctly"},
            domain={"x": [0.5, 0.75], "y": [0, 0.5]},
        )
    )

    return (
        dff["contestant"].squeeze(),
        fig_streak,
        fig_earnings,
        indicator,
        table_clues,
        f"Clues from {champion}'s games ",
    )
