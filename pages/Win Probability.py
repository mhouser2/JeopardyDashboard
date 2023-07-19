import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, Input, Output, dcc, html, register_page, callback
from JeopardyFunctions import final_model_plot_data
from sqlalchemy import create_engine
import os
import plotly.express as px

font_size = 14
database_url = os.getenv("database_url_jeopardy")

register_page(
    __name__,
    path="/WinProbability",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)
explanation_string = (
    "This page visualizes the outputs of a win probability model trained on over 6,600 regular season episodes of Jeopardy. "
    "See [this page](https://github.com/mhouser2/JeopardyDashboard/blob/main/Win%20Probability%20Modeling.ipynb) for details on how the model was designed. "
)


def serve_layout_win_probability():
    engine = create_engine(database_url)
    shows_query = f"""SELECT CONCAT('Show Number #', show_number, ' - ', to_char(air_date, 'Day,  Month DD, YYYY')) FROM games_view where regular_season = true and show_number >= 3966 and winning_contestant <> 'Tied'
    ORDER BY show_number """
    shows = pd.read_sql(shows_query, con=engine).squeeze()
    engine.dispose()

    return dbc.Container(
        [
            html.H1("Win Probability Modelling"),
            dcc.Markdown(explanation_string, style={"fontSize": font_size}),
            dbc.Row(
                dbc.Col(
                    [
                        html.P("Select Episode:"),
                        dcc.Dropdown(
                            id="show-number",
                            options=shows,
                            value=shows.iloc[-1],
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
            ),
            html.Hr(),
            dbc.Row(
                [dbc.Col([dcc.Graph(id="win-probability-graph")], width=11)],
                className="h-75",
            ),
        ],
        fluid=True,
    )


layout = serve_layout_win_probability


@callback(
    Output(component_id="win-probability-graph", component_property="figure"),
    Input(component_id="show-number", component_property="value"),
)
def get_data(show_number):
    show_number = int(show_number.split("#")[1].split(" -")[0])
    dff = final_model_plot_data(show_number)

    scores_melt = dff.melt(
        id_vars=["question_number"],
        value_vars=[
            "contestant_1_score",
            "contestant_2_score",
            "returning_champion_score",
        ],
        var_name="contestant",
    )
    scores_melt["metric"] = "score"
    scores_melt["contestant"] = scores_melt["contestant"].str.split("_score").str[0]

    probability_melt = dff.melt(
        id_vars=["question_number"],
        value_vars=["contestant_1", "contestant_2", "returning_champion"],
        var_name="contestant",
    )
    probability_melt["metric"] = "probability"
    probability_melt["value"] = probability_melt["value"].multiply(100).round(2)

    plot_data = pd.concat([scores_melt, probability_melt], ignore_index=True)
    plot_data["contestant"] = plot_data["contestant"].replace(
        {
            "contestant_1": "Contestant 1",
            "contestant_2": "Contestant 2",
            "returning_champion": "Returning Champion",
        }
    )

    fig = px.line(
        plot_data,
        x="question_number",
        y="value",
        facet_row="metric",
        color="contestant",
        height=1000,
    )
    dd_locations = dff[dff["is_dd"] == 1]["question_number"]

    for i in range(len(dd_locations)):
        fig.add_vline(x=dd_locations.iloc[i], line_color="deeppink", line_dash="dash")
    fig.update_yaxes(matches=None)

    fig.update_layout(
        title_text=f"Show Number {show_number} Scores and Win Probability <br><sup>Dashed pink lines indicate locations of the Daily Double</sup>"
    )
    fig.update_layout(hovermode="x unified")
    fig.update_traces(mode="lines", hovertemplate=None)
    return fig
