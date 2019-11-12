# -*- coding: utf-8 -*-
from logic.utility import Utility
from dash.dependencies import Input, Output
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objs as go
import warnings

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
        self.__u = Utility()
        self.__title = ""
        self.__home_team = ""
        self.__away_team = ""

    def match_header(self):
        """
        :return:
        """
        df = self.__u.load_dataframe("match_header")
        f_match_id = (df.MatchId == self.__match_id)
        self.__home_team = df.loc[f_match_id]['Home'][0]
        self.__away_team = df.loc[f_match_id]['Away'][0]

        df = df[['HomeAwayTeam', 'MatchId']]
        self.__title = df['HomeAwayTeam'].loc[f_match_id][0]
        return [{'label': "   " + row['HomeAwayTeam'], 'value': row['MatchId']} for idx, row in df.iterrows()]

    def final_score(self):
        """
        :return: Final score in formatted output
        """
        df = self.__u.load_dataframe("player_stat")
        f = df.MatchId == self.__match_id
        df = df.loc[f][['HomeAway', 'Made1', 'Made2', 'Made3']]
        df_grouped = df.groupby(['HomeAway']).sum()
        df_grouped['Made2'] = df_grouped['Made2'] * 2
        df_grouped['Made3'] = df_grouped['Made3'] * 3
        df_score = df_grouped.sum(axis=1).reset_index(name='Score')['Score']
        list_score = df_score.tolist()  # first number is Away!
        return str(list_score[1]) + " - " + str(list_score[0])

    def __player_stats(self, home_away):
        """
        :param home_away:
        :param str_match_id:
        :return:
        """
        df = self.__u.load_dataframe("player_stat")
        df = df.loc[(df.HomeAway == home_away) & (df.MatchId == self.__match_id)]
        if home_away == 'Home':
            table_title = self.__home_team
            h3_id = 'h3-home-table'
            table_id = 'stats-home-table'
        else:
            table_title = self.__away_team
            h3_id = 'h3-away-table'
            table_id = 'stats-away-table'

        cols = ['PlayerName', 'Point', 'Foul', 'Made1', 'Missed1', 'Made2', 'Missed2', 'Made3', 'Missed3']
        cols += ['OffensiveRebound', 'DefensiveRebound', 'Assist', 'Turnover', 'Steal', 'Block', 'Efficiency']
        df = df[cols]

        cols = [{"name": i, "id": i} for i in df.columns]
        df_records = df.to_dict("records")

        _return = html.Div([html.H3(table_title, id=h3_id),
                            html.Div(dash_table.DataTable(id=table_id,
                                                          columns=cols,
                                                          data=df_records
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
        difference_data = [{'x': x_difference_minutes_home, 'y': difference_home, 'type': 'bar', 'name': self.__home_team},
                           {'x': x_difference_minutes_away, 'y': difference_away, 'type': 'bar', 'name': self.__away_team}]

        figure_cum_scoring = {"data": accumulation_data,
                            "layout": go.Layout(yaxis={"title": "Points"},
                                                xaxis={"title": "Minute"},
                                                title="Scoring per minute "
                                                )
                            }

        figure_difference =  {"data": difference_data}

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
        df_home = df.loc[f_home][['PlayerName', 'Efficiency']].sort_values(by=['Efficiency'])
        df_away = df.loc[f_away][['PlayerName', 'Efficiency']].sort_values(by=['Efficiency'])
        teams = [self.__home_team, self.__away_team]
        both_figures = []
        for idx, df in enumerate([df_home, df_away]):
            figure = {
                'data': [go.Bar(x=df['Efficiency'],
                                y=df['PlayerName'],
                                orientation='h')],
                'layout': go.Layout(
                    title=teams[idx],
                    xaxis={'title': 'Efficiency'},
                    margin={'l': 200, 'b': 60, 't': 30, 'r': 20}
                )
            }
            both_figures.append(figure)
        _return = html.Div([dcc.Graph(id='graph-cumulative-score-home',
                                      figure=both_figures[0],
                                      config={'staticPlot': True}
                                      ),
                            dcc.Graph(id='graph-cumulative-score-away',
                                      figure=both_figures[1],
                                      config={'staticPlot': True}
                                      )
                           ], style={'width': '75%'})
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
                    'layout': {
                        'title': 'Assists per period'
                    }
        }

        _return = html.Div([dcc.Graph(id='graph-assist',
                            figure=figure,
                            config={'staticPlot': True})
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
              html.H2(id="h2-score"),
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
               Output(component_id='h2-score', component_property='children'),
               Output('tabs-content-example', 'children')],
              [Input('tabs', 'value'),
               Input(component_id='match-radio', component_property='value')])
def render_content(tab, str_match_id):
    if str_match_id != '':
        print(str_match_id)
        logic = Logic(str_match_id)
        match_header = logic.match_header()
        title = logic.get_title()
        final_score = logic.final_score()

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
               final_score, \
               _return


if __name__ == '__main__':
    app.run_server(debug=True)
