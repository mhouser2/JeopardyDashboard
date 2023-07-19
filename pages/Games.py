import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, Input, Output, dcc, html, register_page, callback
from JeopardyFunctions import pivot_game, game_progression
import plotly.express as px
from sqlalchemy import create_engine
import os

font_size = 14
database_url = os.getenv("database_url_jeopardy")


register_page(
    __name__,
    path="/GameSummary",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)

explanation_string = """ This dashboard allows users to view all the clues from previous episodes of Jeopardy. Hovering over the tables will display the correct response. 
The dashboard also shows the final scores for each contestant and the number of correct and incorrect responses. Finally there is a graph that shows the scores of each contestant over time
"""


def serve_layout_games():
    engine = create_engine(database_url)
    shows_query = f"""SELECT CONCAT('Show Number #', show_number, ' - ', to_char(air_date, 'Day,  Month DD, YYYY')) FROM games_view ORDER BY show_number """
    shows = pd.read_sql(shows_query, con=engine).squeeze()

    engine.dispose()
    return dbc.Container(
        [
            html.H1("Game Summary Dashboard"),
            html.P(explanation_string, style={"fontSize": 16}),
            dbc.Row(
                dbc.Col(
                    [
                        dcc.Dropdown(
                            id="show-number",
                            options=shows,
                            value=shows.iloc[-1],
                            clearable=False,
                        )
                    ],
                    width=4,
                ),
            ),
            html.Hr(),
            html.H2("Clues"),
            dbc.Row(id="output-content2"),
        ],
        fluid=True,
    )


layout = serve_layout_games


@callback(
    Output(component_id="output-content2", component_property="children"),
    Input(component_id="show-number", component_property="value"),
)
def get_data(show_number):
    show_number = int(show_number.split("#")[1].split(" -")[0])

    (
        j_clues,
        j_correct_responses,
        dj_clues,
        dj_correct_responses,
        fj_clue,
        fj_response,
    ) = pivot_game(show_number)

    scores, contestants_correct_clues, contestants_incorrect_clues = game_progression(
        show_number
    )
    final_scores = scores.iloc[:, 1:4]
    dds = scores.iloc[:, 4]
    dds_indexes = dds[dds == 1].index
    fig = px.line(final_scores)  # , height=800
    fig.update_layout(hovermode="x unified")
    fig.update_traces(mode="lines", hovertemplate=None)

    for i in range(len(dds_indexes)):
        fig.add_vline(x=dds_indexes[i], line_color="deeppink", line_dash="dash")

    fig.update_layout(
        title=dict(
            text="Contestant Scores over Time <br><sup>Dashed pink lines indicate locations of the Daily Double</sup>",
            font=dict(size=22),
        ),
        xaxis_title="Clue Number",
        yaxis_title="Contestant Score",
        legend_title_text="Contestant",
    )

    j_round_table = dash_table.DataTable(
        data=j_clues.to_dict("records"),
        columns=[{"name": i, "id": i} for i in j_clues.columns],
        style_cell_conditional=[{"if": {"column_id": "clue_value"}, "width": "50px"}],
        style_cell={
            "height": "auto",
            "width": "300px",
            "maxWidth": "300px",
            "whiteSpace": "normal",
            "fontSize": font_size,
        },
        style_data={"whiteSpace": "normal", "height": "20px"},
        fill_width=False,
        tooltip_data=[
            {
                column: {"value": str(value), "type": "markdown"}
                for column, value in row.items()
            }
            for row in j_correct_responses.to_dict("records")
        ],
    )

    dj_round_table = dash_table.DataTable(
        data=dj_clues.to_dict("records"),
        columns=[{"name": i, "id": i} for i in dj_clues.columns],
        style_cell_conditional=[{"if": {"column_id": "clue_value"}, "width": "50px"}],
        style_cell={
            "height": "auto",
            "width": "300px",
            "maxWidth": "300px",
            "whiteSpace": "normal",
            "fontSize": font_size,
        },
        style_data={"whiteSpace": "normal", "height": "auto"},
        fill_width=False,
        tooltip_data=[
            {
                column: {"value": str(value), "type": "markdown"}
                for column, value in row.items()
            }
            for row in dj_correct_responses.to_dict("records")
        ],
    )
    fj_round_table = dash_table.DataTable(
        data=fj_clue.to_dict("records"),
        columns=[{"name": i, "id": i} for i in fj_clue.columns],
        style_cell={
            "height": "auto",
            "minWidth": "250px",
            "width": "250px",
            "maxWidth": "250px",
            "whiteSpace": "normal",
            "fontSize": font_size,
        },
        style_data={"whiteSpace": "normal", "height": "200"},
        fill_width=False,
        tooltip_data=[
            {
                column: {"value": str(value), "type": "markdown"}
                for column, value in row.items()
            }
            for row in fj_response.to_dict("records")
        ],
    )

    score_summary = pd.DataFrame(scores.iloc[-1, 1:4])
    score_summary["correct_responses"] = contestants_correct_clues
    score_summary["incorrect_responses"] = contestants_incorrect_clues
    score_summary.loc["Combined"] = score_summary.sum()
    score_summary = score_summary.reset_index()
    score_summary.columns = [
        "Contestant",
        "Final Score",
        "Correct Responses",
        "Incorrect Responses",
    ]

    summary_table = dash_table.DataTable(
        data=score_summary.to_dict("records"),
        columns=[{"name": i, "id": i} for i in score_summary.columns],
        style_cell={"textAlign": "left"},
        style_data={"whiteSpace": "normal", "height": "auto"},
        fill_width=False,
    )

    return dbc.Col(
        [
            html.H3("Jeopardy Round"),
            dbc.Col(j_round_table, style={"marginBottom": "2.5em"}),
            html.H3("Double Jeopardy Round"),
            dbc.Col(dj_round_table, style={"marginBottom": "2.5em"}),
            html.H3("Final Jeopardy"),
            dbc.Col(fj_round_table, width=4, style={"marginBottom": "2.5em"}),
            html.Hr(),
            html.H2("Game Summary"),
            dbc.Col(summary_table, width=4, style={"marginBottom": "2.5em"}),
            dbc.Row([dbc.Col([dcc.Graph(figure=fig)], width=12)]),
        ],
        width=12,
    )
