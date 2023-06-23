import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import dash_table, Input, Output, dcc, html, register_page
from datetime import date
import plotly.express as px
import numpy as np
from sqlalchemy import create_engine
import os
import psycopg2

database_url = os.getenv("database_url_jeopardy")


register_page(
    __name__,
    path="/CategoryExploration",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)

explanation_string = """This dashboard creates a bar graph of the top 25 categories or correct responses by frequency,
 colored by the percent of clues answered correctly. Clicking on any of the bar graphs allows users to then see all the
 clues in that category, allowing them to practice based on category difficulty. 
"""


def serve_layout_responses():
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    query_max_date = "Select max(air_date) from games_view"
    cur.execute(query_max_date)
    results = cur.fetchone()[0]
    cur.close()
    conn.close()
    return dbc.Container(
        [
            dbc.Row(
                [
                    html.H1("Category Exploration"),
                    html.P(explanation_string, style={"fontSize": 16}),
                    dbc.Col(
                        [
                            html.P("Air Date Range:"),
                            dcc.DatePickerRange(
                                id="air-date-range-category-exploration",
                                min_date_allowed=date(1984, 9, 10),
                                max_date_allowed=results,
                                initial_visible_month=results,
                                end_date=results,
                                start_date=date(1984, 9, 10),
                            ),
                            html.P("Select where to search:"),
                            dbc.Col(
                                dcc.Dropdown(
                                    ["Correct Response", "Category"],
                                    value="Category",
                                    id="search-eda",
                                    clearable=False,
                                ),
                            ),
                            html.P("Input search term:"),
                            dbc.Col(
                                dbc.Input(
                                    id="clue-input-eda",
                                    type="text",
                                    placeholder="Search for term here",
                                    debounce=True,
                                    size="lg",
                                    html_size="30",
                                    value="",
                                ),
                            ),
                            html.P("Number to Offset"),
                            dbc.Col(
                                dbc.Input(
                                    type="number",
                                    min=0,
                                    max=100000,
                                    step=5,
                                    value=0,
                                    id="offset",
                                ),
                                style={"marginBottom": "4.5em"},
                            ),
                        ],
                        width=4,
                    ),
                    dbc.Col([dcc.Graph(id="bar-graph-top")], width=8),
                ]
            ),
            dbc.Row(
                dbc.Col(
                    id="clickdata-clues", width=12
                )  # , style={"marginTop": "2.5em"}
            ),
            dbc.Row(dbc.Col(id="clickdata-responses", width=12)),
        ],
        fluid=True,
    )


layout = serve_layout_responses


@dash.callback(
    Output(component_id="bar-graph-top", component_property="figure"),
    Input(component_id="clue-input-eda", component_property="value"),
    Input(component_id="search-eda", component_property="value"),
    Input(component_id="offset", component_property="value"),
    Input(
        component_id="air-date-range-category-exploration",
        component_property="start_date",
    ),
    Input(
        component_id="air-date-range-category-exploration",
        component_property="end_date",
    ),
)
def plot_categories(search_term, search_destination, offset, start_date, end_date):
    search_destination_sql_dict = {
        "Correct Response": "correct_response",
        "Category": "category",
    }
    search_destination_sql = search_destination_sql_dict[search_destination]

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    clues_columns = [f"{search_destination_sql}", "count", "percent_correct"]
    if search_term != "":
        query_clues = """
            SELECT {search_destination_sql} , COUNT({search_destination_sql}) , SUM(CASE WHEN n_correct >= 1 then 1 else 0 end)::float/COUNT(correct_response) percent_correct
            FROM clues_view
            
            WHERE  {search_destination_sql}  ILIKE '%{search_term}%'  and correct_response <> '=' and air_date between '{start_date}' and '{end_date}'
            GROUP BY {search_destination_sql}
            ORDER BY COUNT(correct_response) desc
            LIMIT 15 OFFSET {offset}
                       """.format(
            search_destination_sql=search_destination_sql,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            search_term=search_term,
        )
    else:
        query_clues = """
                SELECT {search_destination_sql}, COUNT({search_destination_sql}), SUM(CASE WHEN n_correct >= 1 then 1 else 0 end)::float/COUNT(correct_response) percent_correct
                FROM clues_view
                WHERE air_date between '{start_date}' and '{end_date}' and correct_response <> '='
                GROUP BY {search_destination_sql}
                HAVING COUNT(correct_response) > 0
                ORDER BY COUNT({search_destination_sql}) desc
                LIMIT 15 OFFSET {offset}""".format(
            search_destination_sql=search_destination_sql,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
        )

    cur.execute(query_clues)
    results = cur.fetchall()
    dff = pd.DataFrame(results, columns=clues_columns).sort_values(
        "count", ascending=True
    )

    dff["percent_correct"] = dff["percent_correct"].multiply(100).round(2)
    fig = px.bar(
        dff,
        y=f"{search_destination_sql}",
        x="count",
        color="percent_correct",
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=85,
    )
    fig.update_layout(
        title={
            "text": f"{offset}-{15+offset} most frequent {search_destination}",
            "font": {"size": 30},
        },
    )

    return fig


@dash.callback(
    Output(component_id="clickdata-clues", component_property="children"),
    Input(component_id="bar-graph-top", component_property="clickData"),
    Input(component_id="search-eda", component_property="value"),
    Input(
        component_id="air-date-range-category-exploration",
        component_property="start_date",
    ),
    Input(
        component_id="air-date-range-category-exploration",
        component_property="end_date",
    ),
)
def update(clickdata, search_destination, start_date, end_date):
    search_destination_sql_dict = {
        "Correct Response": "correct_response",
        "Category": "category",
    }
    search_destination_sql = search_destination_sql_dict[search_destination]

    search_destination_flipped_dict = {
        "Correct Response": "Category",
        "Category": "Correct Response",
    }
    search_destination_flipped = search_destination_flipped_dict[search_destination]

    if clickdata is None and search_destination == "Category":
        clickdata_y = "SCIENCE"
    elif clickdata is None and search_destination == "Correct Response":
        clickdata_y = "Australia"
    else:
        clickdata_y = clickdata["points"][0]["y"]

    clues_columns = [
        "Air Date",
        "Round",
        "Clue Value",
        "Category",
        "Clue",
        "Number Correct",
        "Correct Response",
    ]
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    query_clues = """
            SELECT air_date, round_id round, clue_value, category, clue, n_correct, correct_response
            FROM clues_view
            WHERE {search_destination_sql} ILIKE '%{term}%' and air_date between '{start_date}' and '{end_date}' 
            ORDER BY air_date desc
            """.format(
        search_destination_sql=search_destination_sql,
        term=clickdata_y,
        start_date=start_date,
        end_date=end_date,
    )
    cur.execute(query_clues)
    results = cur.fetchall()
    dff = pd.DataFrame(results, columns=clues_columns)

    dff["Air Date"] = pd.DatetimeIndex(dff["Air Date"]).strftime("%Y-%m-%d")

    table_clues = dash_table.DataTable(
        data=dff.to_dict("records"),
        columns=[{"name": i, "id": i, "hideable": True} for i in dff.columns],
        style_cell={"textAlign": "left", "height": "auto", "fontSize": 12},
        page_size=8,
        style_data={"whiteSpace": "normal", "height": "auto"},
        sort_action="native",
        filter_action="native",
        export_format="csv",
    )

    pivot_table = dff[dff["Round"] != "FJ"].pivot_table(
        index=f"{search_destination_flipped}",
        values=["Number Correct"],
        aggfunc={"Number Correct": [np.size, np.sum]},
    )
    pivot_table.columns = [" ".join(col) for col in pivot_table.columns.values]
    pivot_table.columns = ["Count", "Answered Correct"]
    pivot_table["Answered Correct %"] = (
        pivot_table["Answered Correct"] / pivot_table["Count"]
    )
    pivot_table = (
        pivot_table.sort_values(by="Count", ascending=False).reset_index().round(2)
    )

    dash_pivot_table = dash_table.DataTable(
        data=pivot_table.to_dict("records"),
        columns=[{"name": i, "id": i} for i in pivot_table.columns],
        page_size=8,
        style_data={"whiteSpace": "normal", "height": "auto"},
        style_cell={"textAlign": "left", "height": "auto", "fontSize": 12},
        sort_action="native",
        filter_action="native",
    )

    return dbc.Row(
        [
            html.H3(f"{search_destination}={clickdata_y}"),
            dbc.Row(dbc.Col(table_clues, width=12)),
            html.H3(
                f"Most Common {search_destination_flipped} for {search_destination}={clickdata_y}"
            ),
            dbc.Row(dbc.Col(dash_pivot_table, width=9)),
        ]
    )
