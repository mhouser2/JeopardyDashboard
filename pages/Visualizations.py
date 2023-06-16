import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, dcc, html, register_page
import plotly.express as px
from datetime import date
from sqlalchemy import create_engine
import os

database_url = os.getenv("database_url_jeopardy")

register_page(
    __name__,
    path="/",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)
explanation_string = (
    "This page showcases data visualizations depicting insightful statistical measures of the Jeopardy clue board, empowering contestants to strategize effectively."
    " The default date range starts on November 26 2001, the first episode in which clue values doubled, however available data dates back to September 10 1984."
)

engine = create_engine(database_url)

max_air_date_query = f"""SELECT MAX(air_date) FROM clues_view 
                            """
max_air_date = pd.read_sql(max_air_date_query, con=engine).squeeze().date()
engine.dispose()

print(max_air_date)

max_air_date_string = max_air_date.strftime("%Y-%m-%d")
layout = dbc.Container(
    [
        html.H1("Data Visualizations"),
        html.P(explanation_string, style={"fontSize": 24}),
        dbc.Row(
            dbc.Col(
                [
                    html.P("Select Show Air Date Range:"),
                    dcc.DatePickerRange(
                        id="air-date-range",
                        min_date_allowed=date(1984, 9, 10),
                        max_date_allowed=max_air_date,
                        initial_visible_month=max_air_date,
                        end_date=max_air_date,
                        start_date=date(2001, 11, 26),
                    ),
                ]
            )
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col([dcc.Graph(id="daily-double-graph")], width=9),
                dbc.Col(
                    [
                        html.P(
                            "This heatmap shows the probability of a particular clue on the board showing the location of the daily double -"
                            " a special clue that allows the contestant to wager however much money they have earned which only they can answer. "
                            "Knowing where the daily double is most likely to show up allows contestants to optimize their strategy. One strategy could be selecting clues with low probabilities of holding the daily double so they can "
                            "increase their score and then searching for the daily double in order to make a high wager. A more conservative strategy is to hunt for daily doubles early to prevent other contestants the opportunity to wager heavily.  ",
                            style={"fontSize": 24},
                        )
                    ],
                    width=3,
                ),
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col([dcc.Graph(id="answer-correct-graph")], width=9),
                dbc.Col(
                    [
                        html.P(
                            "This heatmap shows the probability of a clue being answered correctly by a contestant given its location on the board. As expected, as clue values increase, clue difficulty also increases. "
                            "What's interesting is comparing the clues from the Jeopardy round to the Double Jeopardy round. The $800 clues in the Jeopardy round are slightly more difficult than the $800 clues in the Jeopardy round,"
                            " and the $2000 clues in the Double Jeopardy Round are much more difficult than the $1000 clues in the Jeopardy round. ",
                            style={"fontSize": 24},
                        )
                    ],
                    width=3,
                ),
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col([dcc.Graph(id="expected-value-graph")], width=9),
                dbc.Col(
                    [
                        html.P(
                            "This heatmap shows the expected value of each clue based on its location on the board. Effectively, this means that on average each clue in this location increases all contestants' scores by X amount. This metric combines both the clue's original value, as well as the number of contestants that answered correctly/incorrectly."
                            "What's interesting here is that the $1,600 clues in the Double Jeopardy round are approximately as valuable as the $2,000 clues, because they are comparatively much easier to answer. Additionally, columns 2 and 6 have slightly higher expected values than the other columns, typically because these are more gimmicky categories. ",
                            style={"fontSize": 24},
                        )
                    ],
                    width=3,
                ),
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col([dcc.Graph(id="fj-graph")], width=9),
                dbc.Col(
                    [
                        html.P(
                            "This graph shows the frequency of how many contestants answered Final Jeopardy correctly. Since regular clues are easier and only allow one person to be answered, it's interesting to see how all contestants perform when given the same opportunity against each other.",
                            style={"fontSize": 24},
                        )
                    ],
                    width=3,
                ),
            ]
        ),
    ],
    fluid=True,
)


@dash.callback(
    Output(component_id="answer-correct-graph", component_property="figure"),
    Output(component_id="daily-double-graph", component_property="figure"),
    Output(component_id="expected-value-graph", component_property="figure"),
    Output(component_id="fj-graph", component_property="figure"),
    Input(component_id="air-date-range", component_property="start_date"),
    Input(component_id="air-date-range", component_property="end_date"),
)
def plot_prob_correct(start_date, end_date):
    engine = create_engine(database_url)
    print(end_date)
    print(max_air_date_string)
    if start_date == "2001-11-26" and end_date == max_air_date_string:
        clues_query = f"""
                        SELECT * FROM clue_prob_correct
                        """
    else:
        clues_query = f"""
        SELECT round_id, c.category_column, row_id,  SUM(n_correct)::float/COUNT(n_correct) percent_correct
        FROM clues_view c
        WHERE round_id in ('DJ', 'J') and c.air_date between '{start_date}' and '{end_date}'
        GROUP BY round_id, c.category_column, row_id
        ORDER BY round_id desc, row_id, c.category_column
        """

    clues_df = pd.read_sql_query(clues_query, con=engine)

    columns = [f"Column {i}" for i in range(1, 7)]
    rows = [f"Row {i}" for i in range(1, 6)]

    data_prob = (
        clues_df["percent_correct"].multiply(100).round(2).to_numpy().reshape(2, 5, 6)
    )
    fig_prob = px.imshow(
        data_prob,
        facet_col=0,
        facet_col_wrap=2,
        color_continuous_scale="blues",
        text_auto=True,
        height=800,
        labels=dict(y="Row", color="Percent Answered Correctly"),
        x=columns,
        y=rows,
    )

    fig_prob.layout.annotations[0]["text"] = "Jeopardy Round"
    fig_prob.layout.annotations[1]["text"] = "Double Jeopardy Round"
    fig_prob.update_layout(
        title={
            "text": "Probability of Clue being answered Correctly",
            "font": {"size": 30},
            "xanchor": "center",
            "yanchor": "top",
            "x": 0.5,
            "y": 0.98,
        },
        font={"size": 14},
        margin={"t": 75},
    )
    fig_prob.update_xaxes(visible=False)
    fig_prob.update_yaxes(visible=False)

    if start_date == "2001-11-26" and end_date == max_air_date_string:
        query_dd = f"""
                    SELECT * FROM daily_double_locations
                    """
    else:
        query_dd = f"""
    
        with subq as (SELECT round_id, c.category_column, row_id, CASE WHEN LEFT(value,2) = 'DD' then 1 else 0 end is_dd
        FROM clues_view c
        WHERE round_id in ('DJ', 'J')  and c.air_date between '{start_date}' and '{end_date}'
    
        ORDER BY round_id desc, c.category_column, row_id)
    
        SELECT round_id, subq.category_column, row_id,  SUM(is_dd)::float/(SELECT SUM(is_dd) from subq where round_id = 'J' group by round_id)
        from subq
        WHERE round_id = 'J' 
        group by round_id, subq.category_column, row_id
        UNION 
        SELECT round_id, subq.category_column, row_id,  SUM(is_dd)::float/(SELECT SUM(is_dd) from subq where round_id = 'DJ' group by round_id)
        from subq
        WHERE round_id = 'DJ'
        group by round_id, subq.category_column, row_id
        ORDER BY round_id desc, row_id
        """

    df = pd.read_sql_query(query_dd, con=engine)
    df.columns = ["round", "column", "row", "prob_dd"]

    df = df.sort_values(by=["round", "row", "column"], ascending=[False, True, True])

    data_dd = df["prob_dd"].multiply(100).round(2).to_numpy().reshape(2, 5, 6)
    fig_dd = px.imshow(
        data_dd,
        facet_col=0,
        facet_col_wrap=2,
        color_continuous_scale="blues",
        text_auto=True,
        height=800,
        labels=dict(y="Row", color="Daily Double Probability"),
        x=columns,
        y=rows,
    )
    fig_dd.update_xaxes(side="top")

    fig_dd.layout.annotations[0]["text"] = "Jeopardy Round"
    fig_dd.layout.annotations[1]["text"] = "Double Jeopardy Round"
    fig_dd.update_layout(
        title={
            "text": "Daily Double Location Probability",
            "font": {"size": 30},
            "xanchor": "center",
            "yanchor": "top",
            "x": 0.5,
            "y": 0.98,
        },
        font={"size": 14},
        margin={"t": 75},
    )
    fig_dd.update_xaxes(visible=False)
    fig_dd.update_yaxes(visible=False)

    if start_date == "2001-11-26" and end_date == max_air_date_string:
        query_ev = f"""
        SELECT * FROM clue_ev
        """
    else:
        query_ev = f"""
            SELECT c.round_id, c.category_column, c.row_id, AVG((c.n_correct * clue_value::float - c.n_incorrect * clue_value::float)) earnings
            FROM clues_view c
            WHERE round_id in ('J', 'DJ') and c.air_date between '{start_date}' and '{end_date}' and is_dd = false
            GROUP BY c.round_id, c.row_id, c.category_column
            ORDER BY round_id desc, row_id, c.category_column
        """

    dff_ev = pd.read_sql_query(query_ev, con=engine)
    dff_ev.columns = ["round", "column", "row", "Expected Value"]

    data_ev = dff_ev["Expected Value"].multiply(1).round(2).to_numpy().reshape(2, 5, 6)
    fig_ev = px.imshow(
        data_ev,
        facet_col=0,
        facet_col_wrap=2,
        color_continuous_scale="blues",
        text_auto=True,
        height=800,
        labels=dict(y="Row", color="Clue Location Expected Value"),
        x=columns,
        y=rows,
    )
    fig_ev.update_xaxes(side="top")

    fig_ev.layout.annotations[0]["text"] = "Jeopardy Round"
    fig_ev.layout.annotations[1]["text"] = "Double Jeopardy Round"
    fig_ev.update_layout(
        title={
            "text": "Clue Location Expected Value",
            "font": {"size": 30},
            "xanchor": "center",
            "yanchor": "top",
            "x": 0.5,
            "y": 0.98,
        },
        font={"size": 14},
        margin={"t": 75},
    )
    fig_ev.update_xaxes(visible=False)
    fig_ev.update_yaxes(visible=False)

    if start_date == "2001-11-26" and end_date == max_air_date_string:
        query_fj = f""" SELECT * FROM final_jeopardy_correct
    """
    else:
        query_fj = f"""
    SELECT n_correct, COUNT(n_correct), 100 * COUNT(n_correct)::float/(SELECT COUNT(DISTINCT c.show_number) from games_view g LEFT JOIN clues_view c on c.show_number = g.show_number where regular_season = True and c.air_date between '{start_date}' and '{end_date}')
        FROM clues_view c left join games_view g on g.show_number = c.show_number where round_id = 'FJ' and regular_season = True and c.air_date between '{start_date}' and '{end_date}'
        GROUP BY n_correct
        """

    dff_fj = pd.read_sql_query(query_fj, con=engine)

    dff_fj.columns = [
        "Number of Correct Contestants",
        "Number of Clues",
        "Percent of Clues",
    ]
    dff_fj["Number of Correct Contestants"] = dff_fj[
        "Number of Correct Contestants"
    ].astype("category")
    fig_fj = px.bar(
        dff_fj,
        x="Number of Correct Contestants",
        y="Percent of Clues",
        hover_data=["Number of Clues"],
    )
    fig_fj.update_layout(
        height=800,
        title={
            "text": "Final Jeopardy Results",
            "font": {"size": 30},
            "xanchor": "center",
            "yanchor": "top",
            "x": 0.5,
            "y": 0.98,
        },
        font={"size": 14},
        margin={"t": 75},
    )
    engine.dispose()
    return fig_prob, fig_dd, fig_ev, fig_fj
