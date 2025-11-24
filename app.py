import dash
from dash import html, Dash
import dash_bootstrap_components as dbc
import os

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)
server = app.server
#server.secret_key = os.environ.get("secret_key", "secret")


explanation_string_1 = "Jeopardy! is a trivia game show where 3 contestants compete to earn the highest score. "
explanation_string_2 = (
    "The show is split into three parts: the Jeopardy Round, the Double Jeopardy Round, and Final Jeopardy. "
    "The Jeopardy and Double Jeopardy rounds work the same, 30 clues broken down into 6 categories with 5 clues each. The Jeopardy round has clue values starting at $200 and incrementing by $200 until ending at $1,000, and the Double Jeopardy Round doubles these values. "
    "Final Jeopardy is one clue in which all contestants have the opportunity to answer and can wager their entire score."
)

explanation_string_6 = (
    "Winning Jeopardy requires both a wide array of trivia knowledge and strategy in order to outcompete the other contestants. "
    "These dashboards aim to inform users on both aspects of the game, visualizing important metrics that allow would be contestants to refine their strategy "
    "as well as providing access to over 470,000 clues in order to improve their trivia knowledge. "
)


sidebar = dbc.Nav(
    [
        dbc.NavLink(
            [
                html.Div(page["name"], className="ms-2"),
            ],
            href=page["path"],
            active="exact",
        )
        for page in dash.page_registry.values()
    ],
    vertical=False,
    pills=True,
    className="bg-light",
)

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.Div("Jeopardy Dashboards"),
                    style={"fontSize": 50, "textAlign": "center"},
                ),
                html.P(
                    [
                        explanation_string_1,
                        html.Br(),
                        html.Br(),
                        explanation_string_2,
                        html.Br(),
                        html.Br(),
                        explanation_string_6,
                    ],
                    style={"fontSize": 16},
                ),
            ]
        ),
        dbc.Row([dbc.Col(sidebar, width=6)]),
        html.Hr(),
        dbc.Row([dbc.Col([dash.page_container], width=12)]),
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True)
