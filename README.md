# Jeopardy Dashboard

[This dashboard](https://jeopardydashboard.herokuapp.com/) collects over 475,000 clues from over 8,000 episodes of Jeopardy in order to provide users with insightful analysis of the history of the show and the opportunity to practice their trivia skills. 

Dashboards include visualizations of important statistical measures such as the location of daily doubles and clue expected values, self-serve dashboards that provide users the opportunity to look at the most common categories and correct responses, and overviews of Jeopardy episodes and champions.

The data was scraped using the Python package Scrapy, and stored in a Postgresql database hosted on Heroku. The dashboard is made using Plotly Dash. 
