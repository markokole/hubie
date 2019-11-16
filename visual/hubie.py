# -*- coding: utf-8 -*-
from logic.utility import Utility
from dash.dependencies import Input, Output
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objs as go
import warnings
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)

warnings.simplefilter(action='ignore', category=FutureWarning)


class Logic:
    """
    """

    def __init__(self, str_match_id=7032956):
        """
        Initialize the instance of Logic object
        :param str_match_id: id of the match that is being visualized
        """
        self.__match_id = int(str_match_id)
        self.__u = Utility(self.__match_id)
        self.__title = ""
        self.__home_team = ""
        self.__away_team = ""

    def match_header(self):
        """
        :return:
        """
        df = self.__u.load_dataframe("match_header").sort_values(by='Match Date')

        dict_all_headers = df.to_dict(orient='records')
        f_match_id = (df.MatchId == self.__match_id)
        single_match = df.loc[f_match_id].to_dict(orient='records')[0]
        self.__home_team = single_match['HomeTeam']
        self.__away_team = single_match['AwayTeam']
        home_score = single_match['Score Home']
        away_score = single_match['Score Away']

        self.__title = "   {} {}:{} {}".format(self.__home_team, home_score, away_score, self.__away_team)

        all_game_headers = [{'label': "   {}: {} {}:{} {}".format(row['Short Date'], row['HomeTeam'], row['Score Home'],
                                                                  row['Score Away'], row['AwayTeam']),
                             'value': row['MatchId']}
                            for row in dict_all_headers]

        return all_game_headers

    def __player_stats(self, home_away):
        """
        :param home_away:
        :return:
        """
        df_all = self.__u.load_dataframe("player_stat")
        print(df_all.columns)
        f_team = (df_all.HomeAway == home_away) & (df_all.MatchId == self.__match_id)
        df = df_all.loc[f_team]

        if home_away == 'Home':
            table_title = self.__home_team
            h3_id = 'h3-home-table'
            table_id = 'stats-home-table'
        else:
            table_title = self.__away_team
            h3_id = 'h3-away-table'
            table_id = 'stats-away-table'

        # define columns to display and correct order
        columns = ['Player', 'Points', '2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA']
        columns = columns + ['DREB', 'OREB', 'REB', 'AST', 'STL', 'TOV', 'BLK', 'FLS', 'Efficiency']

        cols = [{"name": c, "id": c} for c in columns]
        df_records = df[columns].to_dict("records")

        # conditional formatting
        max_eff = df_all.loc[f_team]['Efficiency'].agg(['max']).to_dict()['max']
        max_points = df_all.loc[f_team]['Points'].agg(['max']).to_dict()['max']
        dict_if_eff_max = {'column_id': 'Efficiency', 'filter_query': '{Efficiency} eq ' + str(max_eff)}
        dict_if_eff_min = {'column_id': 'Efficiency', 'filter_query': '{Efficiency} < 0'}
        dict_if_pts_max = {'column_id': 'Points', 'filter_query': '{Points} eq ' + str(max_points)}

        _return = html.Div([html.H3(table_title, id=h3_id),
                            html.Div(dash_table.DataTable(id=table_id,
                                                          columns=cols,
                                                          data=df_records,
                                                          style_data_conditional=[
                                                              {
                                                                  'if': {'row_index': 'odd'},
                                                                  'backgroundColor': 'rgb(248, 248, 248)'
                                                              },
                                                              {
                                                                  'if': {'column_id': 'Efficiency'},
                                                                  'backgroundColor': 'rgb(230, 230, 230)'
                                                              },
                                                              {
                                                                  'if': dict_if_eff_max,
                                                                  'backgroundColor': 'green'
                                                              },
                                                              {
                                                                  'if': dict_if_eff_min,
                                                                  'color': 'red'
                                                              },
                                                              {
                                                                  'if': dict_if_pts_max,
                                                                  'color': 'green'
                                                              },
                                                              {
                                                                  'if': {'column_id': 'Player'},
                                                                  'textAlign': 'left',
                                                                  'width': '200'
                                                              },
                                                              {
                                                                  'if': {'column_id': 'Player'},
                                                                  'width': '300px'
                                                              }
                                                          ],
                                                          style_header={
                                                              'backgroundColor': 'rgb(230, 230, 230)',
                                                              'fontWeight': 'bold'
                                                          }
                                                          )
                                     )
                            ])

        return _return

    def box_score(self):
        """
        :return: Div component with two tables - one for each team - with player statistics
        """
        list_div = []
        for ha in ['Home', 'Away']:
            div = self.__player_stats(ha)
            list_div.append(div)

        df = self.__u.load_dataframe("player_stat")

        _return = html.Div([list_div[0], list_div[1]])
        return _return

    def cumulative_scoring_data(self):
        """
        Prepare an object so the it can be outputed to the graph
        :return: Returns an object that is a property 'data' for the graph component
        """

        # prepare series for cumulative graph
        df = self.__u.load_dataframe("cumulative_score")
        df = df.loc[df.MatchId == self.__match_id]
        x_minutes = df['MinuteRound']
        y_home = df['Home']
        y_away = df['Away']

        # create two series - one with positive Difference for Home team, and negative for Away team
        df_difference_home = df[['MinuteRound', 'Difference']].loc[df.Difference >= 0]
        difference_home = df_difference_home['Difference']
        x_difference_minutes_home = df_difference_home['MinuteRound']
        df_difference_away = df[['MinuteRound', 'Difference']].loc[df.Difference < 0]
        difference_away = df_difference_away['Difference']
        x_difference_minutes_away = df_difference_away['MinuteRound']

        # data for accumulated graph
        accumulation_data = [go.Scatter(x=x_minutes, y=y_home, name=self.__home_team),
                             go.Scatter(x=x_minutes, y=y_away, name=self.__away_team)]

        # data for difference graph
        difference_data = [
            {'x': x_difference_minutes_home, 'y': difference_home, 'type': 'bar', 'name': self.__home_team},
            {'x': x_difference_minutes_away, 'y': difference_away, 'type': 'bar', 'name': self.__away_team}]

        figure_cum_scoring = {"data": accumulation_data,
                              "layout": go.Layout(yaxis={"title": "Points"},
                                                  xaxis={"title": "Minute"},
                                                  title="Scoring per minute "
                                                  )
                              }

        figure_difference = {"data": difference_data}

        _return = html.Div([dcc.Graph(id='graph-cumulative-score',
                                      figure=figure_cum_scoring),
                            dcc.Graph(id='graph-difference',
                                      figure=figure_difference)
                            ],
                           style={'width': '75%'})
        return _return

    def data_efficiency(self):
        """
        :return:
        """
        df = self.__u.load_dataframe("player_stat")
        df = df.loc[(df.MatchId == self.__match_id)]
        f_home = (df.HomeAway == 'Home')
        f_away = (df.HomeAway == 'Away')
        df_home = df.loc[f_home][['Player', 'Efficiency']].sort_values(by=['Efficiency'])
        df_away = df.loc[f_away][['Player', 'Efficiency']].sort_values(by=['Efficiency'])
        dict_min_max = df['Efficiency'].agg(['min', 'max']).to_dict()
        min_eff = dict_min_max['min']
        max_eff = dict_min_max['max']
        teams = [self.__home_team, self.__away_team]
        both_figures = []
        for idx, df in enumerate([df_home, df_away]):
            figure = {
                'data': [go.Bar(x=df['Efficiency'],
                                y=df['Player'],
                                orientation='h')],
                'layout': go.Layout(
                    title=teams[idx],
                    xaxis={'title': 'Efficiency', 'range': [min_eff, max_eff]},
                    margin={'l': 200, 'b': 60, 't': 30, 'r': 20},
                )
            }
            both_figures.append(figure)
        _return = html.Div([html.Tr([html.Th(dcc.Graph(id='graph-cumulative-score-home',
                                                       figure=both_figures[0]
                                                       )),
                                     html.Th(dcc.Graph(id='graph-cumulative-score-away',
                                                       figure=both_figures[1]
                                                       ))])
                            ])
        return _return

    def assist(self):
        df = self.__u.load_dataframe("assists")
        f_match_id = df.MatchId == self.__match_id

        columns = ['Assist', 'PeriodName', 'Team', 'HomeAway']
        df_assist = df.loc[f_match_id][columns].groupby(['PeriodName', 'Team', 'HomeAway']).count().reset_index()
        home_assist = df_assist.loc[df_assist.HomeAway == 'Home']['Assist'].tolist()
        away_assist = df_assist.loc[df_assist.HomeAway == 'Away']['Assist'].tolist()
        df_period = df_assist['PeriodName'].unique()

        figure = {'data': [
            {'x': df_period, 'y': home_assist, 'type': 'bar', 'name': self.__home_team},
            {'x': df_period, 'y': away_assist, 'type': 'bar', 'name': self.__away_team},
        ],
            'layout': go.Layout(
                title='Assists per period',
                xaxis={'title': 'Period'}
            )
        }

        # assist per team per starter/non starter
        df = df[['PlayerId', 'Assist', 'Team', 'HomeAway', 'MatchId']].loc[df.MatchId == self.__match_id]
        df_count = df.groupby(['PlayerId', 'Assist', 'Team', 'HomeAway']).count().reset_index()
        df_count = df_count.rename(columns={'MatchId': 'NoAssists'})
        df_count['Starter'] = df_count['PlayerId'].replace(self.__u.dict_starters)
        df_count = df_count[['Team', 'HomeAway', 'Starter', 'NoAssists']]

        df_count = df_count.groupby(['Team', 'HomeAway', 'Starter']).sum().reset_index()
        print(df_count)
        x_axis = df_count.Team.unique()
        y_trace1 = df_count.loc[df_count.Starter == 'Y']['NoAssists'].tolist()
        name_trace1 = "Starters"
        y_trace2 = df_count.loc[df_count.Starter == 'N']['NoAssists'].tolist()
        name_trace2 = "Bench"
        trace1 = go.Bar(
            x=x_axis,
            y=y_trace1,
            name=name_trace1
        )
        trace2 = go.Bar(
            x=x_axis,
            y=y_trace2,
            name=name_trace2
        )

        figure2 = {'data': [trace1, trace2],
                   'layout': go.Layout(
                       title='Assist distribution between starters and bench',
                       xaxis={'title': 'Team'},
                       barmode="stack"
                   )
                   }

        _return = html.Div([html.Tr([html.Th(dcc.Graph(id='graph-assist',
                                                       figure=figure
                                                       # config={'staticPlot': True}
                                                       )), html.Th(dcc.Graph(id='stack-graph-assist',
                                                                             figure=figure2))])
                            ])

        return _return

    ########
    # Getters
    ########

    def get_match_id(self):
        return self.__match_id

    def get_title(self):
        return self.__title

    def get_home_team(self):
        return self.__home_team

    def get_away_team(self):
        return self.__away_team


logic = Logic()
match_id = logic.get_match_id()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div([html.H3('BLNO Kvinner Grunnserie'),
              dcc.RadioItems(id='match-radio',
                             value=match_id,
                             labelStyle={'display': 'block',
                                         'font': '16px Roboto, sans-serif',
                                         'border': '1px solid #ddd',
                                         'background-color': 'blue',
                                         'color': 'white',
                                         'margin-left': '-20px',
                                         'cursor': 'pointer',
                                         'padding': '20px 0px'
                                         }
                             )
              ], className="split left"),
    html.Div([html.H1(id="h1-title"),

              dcc.Tabs(id="tabs", value='scoring', children=[
                  dcc.Tab(label='Scoring', value='scoring'),
                  dcc.Tab(label='Box Score', value='box-score'),
                  dcc.Tab(label='Efficiency', value='efficiency'),
                  dcc.Tab(label='Assist', value='assist')
              ]),
              html.Div(id='tabs-content-example'),
              html.Br(),
              html.Br(),
              html.Br()],
             className="split right"
             )
])


@app.callback([Output(component_id='match-radio', component_property='options'),
               Output(component_id='h1-title', component_property='children'),
               Output('tabs-content-example', 'children')],
              [Input('tabs', 'value'),
               Input(component_id='match-radio', component_property='value')])
def render_content(tab, str_match_id):
    if str_match_id != '':
        print(str_match_id)
        logic = Logic(str_match_id)
        match_header = logic.match_header()
        title = logic.get_title()

        if tab == 'scoring':
            _return = logic.cumulative_scoring_data()
        elif tab == 'box-score':
            _return = logic.box_score()
        elif tab == 'efficiency':
            _return = logic.data_efficiency()
        elif tab == 'assist':
            _return = logic.assist()

        return match_header, \
               title, \
               _return


if __name__ == '__main__':
    app.run_server(debug=True)
