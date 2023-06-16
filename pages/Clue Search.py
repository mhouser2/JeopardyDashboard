import dash_bootstrap_components as dbc
from dash import Dash, dash_table, Input, Output, dcc, html, register_page, callback
import pandas as pd
import numpy as np
from JeopardyFunctions import find_data
import plotly.express as px
import os

database_url = os.getenv("database_url_jeopardy")


register_page(
    __name__,
    path="/ClueSearch",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)
explanation_string = """This dashboard allows users to search for their desired term in either the the category, correct response, or clue columns in the database. This allows users to 
search for specific terms in order to refresh their memory or improve their weaknesses. The dashboard also aggregates the category and correct response and shows how often they appeared and the percent of clues that were answered correctly, 
allowing users to identify strength/weaknesses in categories across all contestants.
"""

layout = dbc.Container(
    [
        html.H1("Clue Search Dashboard"),
        html.P(explanation_string, style={"fontSize": 24}),
        html.Hr(),
        html.P("Input search term:"),
        dbc.Col(
            dbc.Input(
                id="clue-input",
                type="text",
                placeholder="Search for term here",
                debounce=True,
                size="lg",
                html_size="30",
                value="History",
            ),
            width=2,
        ),
        html.P("Search type:"),
        dbc.Col(
            dcc.Dropdown(
                ["Exact", "Contains"],
                value="Contains",
                id="search-type",
                clearable=False,
            ),
            width=2,
        ),
        html.P("Select where to search:"),
        dbc.Col(
            dcc.Dropdown(
                ["Clue", "Category", "Correct Response"],
                value="Category",
                id="search",
                clearable=False,
            ),
            width=2,
        ),
        html.Hr(),
        dbc.Row(id="output-content"),
    ],
    fluid=True,
)


@callback(
    Output(component_id="output-content", component_property="children"),
    Input("clue-input", "value"),
    Input("search", "value"),
    Input("search-type", "value"),
)
def filter_clues(clue_input, search, search_type):
    if clue_input is None or len(clue_input) <= 2:
        return None
    else:
        dff = find_data(search, clue_input, search_type)
        dff["Correct Response"] = dff["Correct Response"].str.title()
        if dff.empty:
            return None
        else:
            dff["Air Date"] = pd.DatetimeIndex(dff["Air Date"]).strftime("%Y-%m-%d")
            data_to_show = dff[
                [
                    "Air Date",
                    "Round",
                    "Clue Value",
                    "Category",
                    "Clue",
                    "Number Correct",
                    "Correct Response",
                ]
            ]

            crs = dff[
                [
                    "Air Date",
                    "Round",
                    "Clue Value",
                    "Category",
                    "Correct Response",
                    "Number Correct",
                ]
            ]
            crs.columns = [
                "Air Date",
                "Round",
                "Clue Value",
                "Category",
                "Clue",
                "Number Correct",
            ]

            table = dash_table.DataTable(
                data=data_to_show.to_dict("records"),
                columns=[
                    {"name": i, "id": i, "hideable": True} for i in data_to_show.columns
                ],
                style_cell={"textAlign": "left", "height": "auto"},
                tooltip_data=[
                    {
                        column: {"value": str(value), "type": "markdown"}
                        for column, value in row.items()
                    }
                    for row in crs.to_dict("records")
                ],
                page_size=15,
                style_data={"whiteSpace": "normal", "height": "auto"},
                sort_action="native",
                filter_action="native",
                export_format="csv",
            )
            crs.columns = [
                "Air Date",
                "Round",
                "Clue Value",
                "Category",
                "Correct Response",
                "Number Correct",
            ]

            pt = crs[crs["Round"] != "FJ"].pivot_table(
                index="Correct Response",
                values=["Number Correct"],
                aggfunc={"Number Correct": [np.size, np.sum]},
            )
            pt.columns = [" ".join(col) for col in pt.columns.values]
            pt.columns = ["Count", "Answered Correct"]
            pt["Answered Correct %"] = pt["Answered Correct"] / pt["Count"]
            pt = pt.sort_values(by="Count", ascending=False).reset_index().round(2)

            table2 = dash_table.DataTable(
                data=pt.to_dict("records"),
                columns=[{"name": i, "id": i} for i in pt.columns],
                page_size=10,
                style_data={"whiteSpace": "normal", "height": "auto"},
                style_cell={"textAlign": "left", "height": "auto"},
                sort_action="native",
                filter_action="native",
            )

            pt2 = crs[crs["Round"] != "FJ"].pivot_table(
                index="Category",
                values=["Number Correct"],
                aggfunc={"Number Correct": [np.size, np.sum]},
            )
            pt2.columns = [" ".join(col) for col in pt2.columns.values]
            pt2.columns = ["Count", "Answered Correct"]
            pt2["Answered Correct %"] = pt2["Answered Correct"] / pt2["Count"]
            pt2 = pt2.sort_values(by="Count", ascending=False).reset_index().round(2)

            table3 = dash_table.DataTable(
                data=pt2.to_dict("records"),
                columns=[{"name": i, "id": i} for i in pt2.columns],
                page_size=10,
                style_data={"whiteSpace": "normal", "height": "auto"},
                style_cell={"textAlign": "left", "height": "auto"},
                sort_action="native",
                filter_action="native",
            )

            return dbc.Row(
                [
                    html.H2("Clues and Correct Responses"),
                    dbc.Col(table, width=10),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(
                                [html.H2("Correct Response Summary"), table2], width=5
                            ),
                            dbc.Col([html.H2("Category Summary"), table3], width=5),
                        ]
                    ),
                ]
            )
