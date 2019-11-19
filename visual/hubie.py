# -*- coding: utf-8 -*-
from dash.dependencies import Input, Output
import dash
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objs as go
import warnings
import pandas as pd
import boto3

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
warnings.simplefilter(action='ignore', category=FutureWarning)

box_score_star_text = "* - player is starter."
efficiency_explanation_text1 = """Efficiency is calculated using Euroleague formula:"""
efficiency_explanation_text2 = """(Points + Rebounds + Assists + Steals + Blocks + Fouls Drawn)
        - (Missed Field Goals + Missed Free Throws + Turnovers + Shots Rejected + Fouls Committed)"""
efficiency_explanation_text3 = """'Fouls Drawn' and 'Shots Rejected' are not in the equation since they are not registered in the play-by-play data."""

efficiency_explanation = html.Div([html.P(children=efficiency_explanation_text1),
                                   html.B(children=efficiency_explanation_text2),
                                   html.P(children=efficiency_explanation_text3)])


def style_data_conditional_box_score(max_eff):
    style_data_conditional_box_score = [
        {
            'if': {'column_id': 'Efficiency', 'filter_query': '{Efficiency} < 0'},
            'color': 'red'
        },
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': 'rgb(248, 248, 248)'
        },
        {
            'if': {'column_id': 'Efficiency'},
            'backgroundColor': 'rgb(230, 230, 230)'
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
    ]

    # team max eff
    dict_if_eff_max = {'column_id': 'Efficiency', 'filter_query': '{Efficiency} eq ' + str(max_eff)}
    condition_max_eff_home = {
        'if': dict_if_eff_max,
        'backgroundColor': 'green'
    }
    style_data_conditional_box_score.append(condition_max_eff_home)
    return style_data_conditional_box_score


class Logic:
    """
    """

    def __init__(self, str_match_id=7032979):
        """
        Initialize the instance of Logic object
        :param str_match_id: id of the match that is being visualized
        """
        self.__match_id = int(str_match_id)
        # self.__u = Analysis(match_id=self.__match_id) #Utility(self.__match_id)
        self.__home_team = ""
        self.__away_team = ""
        self.__max_eff_home = ""
        self.__max_eff_away = ""
        # define columns to display and correct order
        self.__cols_box_score = ['Player', 'MIN', 'Points', '2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA']
        self.__cols_box_score = self.__cols_box_score + ['DREB', 'OREB', 'REB', 'AST', 'STL', 'TOV', 'BLK', 'FLS',
                                                         'Efficiency']

        self.df_match_list = pd.DataFrame()
        self.__df_player_stat = self.load_dataframe("player_stat")
        self.__df_cumulative_score = self.load_dataframe("cumulative_score")
        self.__df_assist = self.load_dataframe("assists")

    def load_dataframe(self, name):
        # self.__name = name
        s3 = boto3.resource('s3')
        bucket_name = "hubie"
        bucket = s3.Bucket(bucket_name)
        path = "blno/" + name
        df = pd.DataFrame()
        for obj in bucket.objects.filter(Prefix=path):
            file_name = obj.key
            if file_name.find('json') != -1:
                obj = s3.Object(bucket_name, file_name)
                body = obj.get()['Body'].read()
                df_tmp = pd.read_json(body, lines=True)
                df = df.append(df_tmp)

        return df

    def match_list(self):
        """
        :return:
        """
        df = self.load_dataframe("match_header").sort_values(by='Match Date')
        self.df_match_list = df
        dict_all_headers = df.to_dict(orient='records')
        all_game_headers = [{'label': "   {}: {} {}:{} {}".format(row['Short Date'], row['HomeTeam'], row['Score Home'],
                                                                  row['Score Away'], row['AwayTeam']),
                             'value': row['MatchId']}
                            for row in dict_all_headers]

        return all_game_headers

    def match_title(self, match_id):
        df = self.df_match_list
        f_match_id = (df.MatchId == match_id)
        single_match = df.loc[f_match_id].to_dict(orient='records')[0]
        self.__home_team = single_match['HomeTeam']
        self.__away_team = single_match['AwayTeam']
        home_score = single_match['Score Home']
        away_score = single_match['Score Away']

        title = "   {} {}:{} {}".format(self.__home_team, home_score, away_score, self.__away_team)
        return title

    def cumulative_score(self, match_id):
        df = self.__df_cumulative_score
        _df_temp = self.match_title(match_id)  # refresh home & away team values
        f_match = df.MatchId == match_id
        df = df.loc[f_match]
        x_minutes = df['MinuteRound']
        y_home = df['Home']
        y_away = df['Away']

        # data for accumulated graph
        accumulation_data = [go.Scatter(x=x_minutes, y=y_home, name=self.get_home_team()),
                             go.Scatter(x=x_minutes, y=y_away, name=self.get_away_team())]

        figure_cum_scoring = {"data": accumulation_data,
                              "layout": go.Layout(yaxis={"title": "Points"},
                                                  xaxis={"title": "Minute"},
                                                  title="Scoring per minute "
                                                  )
                              }

        # create two series - one with positive Difference for Home team, and negative for Away team
        df_difference_home = df[['MinuteRound', 'Difference']].loc[df.Difference >= 0]
        difference_home = df_difference_home['Difference']
        x_difference_minutes_home = df_difference_home['MinuteRound']
        df_difference_away = df[['MinuteRound', 'Difference']].loc[df.Difference < 0]
        difference_away = df_difference_away['Difference']
        x_difference_minutes_away = df_difference_away['MinuteRound']

        # data for difference graph
        difference_data = [
            {'x': x_difference_minutes_home, 'y': difference_home, 'type': 'bar', 'name': self.__home_team},
            {'x': x_difference_minutes_away, 'y': difference_away, 'type': 'bar', 'name': self.__away_team}]
        figure_difference = {"data": difference_data}

        return figure_cum_scoring, figure_difference

    def box_score(self, match_id):
        df = self.__df_player_stat
        f_match = df.MatchId == match_id
        df = df.loc[f_match]

        df['MIN'] = df.MIN.astype(str).str[-10:-5]

        self.__max_eff_home = df.loc[df.HomeAway == 'Home']['Efficiency'].agg(['max']).to_dict()['max']
        self.__max_eff_away = df.loc[df.HomeAway == 'Away']['Efficiency'].agg(['max']).to_dict()['max']
        return df.loc[df.HomeAway == 'Home'][self.__cols_box_score].to_dict(orient='records'), \
               df.loc[df.HomeAway == 'Away'][self.__cols_box_score].to_dict(orient='records')

    def data_efficiency(self, match_id):
        df = self.__df_player_stat
        df = df.loc[(df.MatchId == match_id)]
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

        return both_figures

    def assist(self, match_id):
        df = self.__df_assist
        f_match_id = df.MatchId == match_id

        columns = ['Assist', 'PeriodName', 'Team', 'HomeAway']
        df_assist = df.loc[f_match_id][columns].groupby(['PeriodName', 'Team', 'HomeAway']).count().reset_index()
        home_assist = df_assist.loc[df_assist.HomeAway == 'Home']['Assist'].tolist()
        away_assist = df_assist.loc[df_assist.HomeAway == 'Away']['Assist'].tolist()
        df_period = df_assist['PeriodName'].unique()

        figure_assist = {'data': [
            {'x': df_period, 'y': home_assist, 'type': 'bar', 'name': self.__home_team},
            {'x': df_period, 'y': away_assist, 'type': 'bar', 'name': self.__away_team},
        ],
            'layout': go.Layout(
                title='Assists per period',
                xaxis={'title': 'Period'}
            )
        }

        # assist per team per starter/non starter
        df = df[['PlayerId', 'Assist', 'Team', 'HomeAway', 'MatchId', 'Starter']].loc[df.MatchId == match_id]
        df_count = df.groupby(['PlayerId', 'Assist', 'Team', 'HomeAway', 'Starter']).count().reset_index()
        df_count = df_count.rename(columns={'MatchId': 'NoAssists'})
        df_count = df_count[['Team', 'HomeAway', 'Starter', 'NoAssists']]

        df_count = df_count.groupby(['Team', 'HomeAway', 'Starter']).sum().reset_index()
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

        figure_assist_starter_bench = {'data': [trace1, trace2],
                                       'layout': go.Layout(
                                           title='Assist distribution between starters and bench',
                                           xaxis={'title': 'Team'},
                                           barmode="stack"
                                       )
                                       }

        return figure_assist, figure_assist_starter_bench

    def get_box_score_cols(self):
        columns = self.__cols_box_score
        return [{'name': i, 'id': i} for i in columns]

    def get_home_team(self):
        return self.__home_team

    def get_away_team(self):
        return self.__away_team

    def get_max_eff_home(self):
        return self.__max_eff_home

    def get_max_eff_away(self):
        return self.__max_eff_away


logic = Logic()

leagues = ['BLNO Kvinner Grunnserie']#, 'BLNO Menn Grunnserie']

######
style_header_box_score = {'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}

#######
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Hubie'
app.layout = html.Div([html.Div([dcc.Store(id='memory-title'),
                                 dcc.Store(id='memory-cumulative-score-data'),
                                 dcc.Store(id='memory-difference-data'),
                                 dcc.Store(id='memory-box-score-columns'),
                                 dcc.Store(id='memory-box-score-home-data'),
                                 dcc.Store(id='memory-box-score-away-data'),
                                 dcc.Store(id='memory-efficiency-home-data'),
                                 dcc.Store(id='memory-efficiency-away-data'),
                                 dcc.Store(id='memory-assists-data'),
                                 dcc.Store(id='memory-assists-starter-bench-data'),
                                 html.Div([
                                     html.H4(children='Pick a league:'),
                                     dcc.RadioItems(
                                         id='league-dropdown',
                                         options=[{'label': k, 'value': k} for k in leagues],
                                         value=leagues[0]
                                     ),
                                     html.Br(),
                                     html.H5(children='Pick a match:'),
                                     dcc.RadioItems(id='match-dropdown'),
                                     dcc.Dropdown(id='dropdown-match',
                                                  options=logic.match_list(),
                                                  value=7032979
                                                 )
                                 ])
                                 ],
                                className="split left"),
                       html.Div([html.H1(id="h1-title"),
                                 dcc.Tabs(id="tabs",
                                          value='tab-scoring',
                                          children=[dcc.Tab(label='Scoring',
                                                            value='tab-scoring',
                                                            children=[html.Div([dcc.Graph(id='graph-cumulative-score'),
                                                                          html.Br(),
                                                                          dcc.Graph(id='graph-difference')],
                                                                         style={'width': '75%'}
                                                                         )]
                                                            ),
                                                    dcc.Tab(label='Box Score',
                                                            value='tab-box-score',
                                                            children=[html.P(children=box_score_star_text),
                                                                      efficiency_explanation,
                                                                      html.H3(id='h3-box-score-title-home'),
                                                                      dash_table.DataTable(id='table-box-score-home',
                                                                                           style_header=style_header_box_score),
                                                                      html.Br(),
                                                                      html.H3(id='h3-box-score-title-away'),
                                                                      dash_table.DataTable(id='table-box-score-away',
                                                                                           style_header=style_header_box_score),
                                                                      html.Br(),
                                                                      html.Br()]
                                                            ),
                                                    dcc.Tab(label='Efficiency',
                                                            value='efficiency',
                                                            children=[html.Div([html.Div([html.Br(),
                                                                                          dcc.Graph(
                                                                                              id='graph-efficiency-home'
                                                                                              )]
                                                                                         , className="six columns"),
                                                                                html.Div([html.Br(),
                                                                                          dcc.Graph(
                                                                                              id='graph-efficiency-away'
                                                                                              )]
                                                                                         , className="six columns")
                                                                                ],
                                                                               className="row")]
                                                            ),
                                                    dcc.Tab(label='Assist',
                                                            value='assist',
                                                            children=[html.Br(),
                                                                      html.Div([
                                                                          html.Div(dcc.Graph(id='graph-assist')
                                                                                   , className="six columns"),
                                                                          html.Div(dcc.Graph(id='stack-graph-assist')
                                                                                   , className="six columns"),
                                                                      ], className="row")]
                                                            )
                                                    ])
                                 ],
                                className="split right")
                       ])


###################################
########### Callbacks #############
###################################

#####################
# left menu
@app.callback(
    Output('dropdown-match', 'options'),
    [Input('league-dropdown', 'value')])
def set_match_options(selected_league):
    print(selected_league)
    if selected_league == 'BLNO Kvinner Grunnserie':
        return logic.match_list()
    else:
        data = {1: 'game1', 2: 'game2', 3: 'game3'}
        dummy = [{'label': v, 'value': k} for k, v in data.items()]
        return dummy

@app.callback(
    Output('dropdown-match', 'value'),
    [Input('dropdown-match', 'options')])
def set_match_value(leagues):
    return leagues[0]['value']

'''@app.callback(
    Output('display-selected-values', 'children'),
    [Input('league-dropdown', 'value'),
     Input('dropdown-match', 'value')])
def set_display_children(selected_league, selected_match):
    return u'Showing match {} in league {}'.format(
        selected_match, selected_league,
    )
'''
###################################

###################################
# Match title
@app.callback([Output('memory-title', 'data'),
               Output('h3-box-score-title-home', 'children'),
               Output('h3-box-score-title-away', 'children')],
              [Input('dropdown-match', 'value')])
def memory_title(str_match_id):
    _return = logic.match_title(int(str_match_id))
    title_home = logic.get_home_team()
    title_away = logic.get_away_team()
    return _return, title_home, title_away


@app.callback(Output('h1-title', 'children'),
              [Input('memory-title', 'data')])
def set_h1_title(data):
    if data is None:
        raise PreventUpdate
    return data


###################################

###################################
# cumulative score
@app.callback([Output('memory-cumulative-score-data', 'data'),
               Output('memory-difference-data', 'data')
               ],
              [Input('dropdown-match', 'value')])
def memory_cumulative_score(str_match_id):
    _return_cumulative_score, _return_difference = logic.cumulative_score(int(str_match_id))
    return _return_cumulative_score, _return_difference


@app.callback([Output('graph-cumulative-score', 'figure'),
               Output('graph-difference', 'figure')],
              [Input('memory-cumulative-score-data', 'data'),
               Input('memory-difference-data', 'data')])
def set_graph_cumulative_score(data_cum_score, data_difference):
    if (data_cum_score is None) | (data_difference is None):
        raise PreventUpdate
    return data_cum_score, data_difference


###################################


###################################
# box-score
@app.callback([Output('memory-box-score-columns', 'data'),
               Output('memory-box-score-home-data', 'data'),
               Output('memory-box-score-away-data', 'data')],
              [Input('dropdown-match', 'value')])
def memory_box_score(str_match_id):
    print(str_match_id)
    return_cols = logic.get_box_score_cols()
    return_data_home, return_data_away = logic.box_score(int(str_match_id))
    return return_cols, return_data_home, return_data_away


@app.callback([Output('table-box-score-home', 'columns'),
               Output('table-box-score-home', 'data'),
               Output('table-box-score-home', 'style_data_conditional'),
               Output('table-box-score-away', 'columns'),
               Output('table-box-score-away', 'data'),
               Output('table-box-score-away', 'style_data_conditional')],
              [Input('memory-box-score-columns', 'data'),
               Input('memory-box-score-home-data', 'data'),
               Input('memory-box-score-away-data', 'data')])
def set_box_score(data_cols, data_home, data_away):
    if (data_cols is None) | (data_home is None) | (data_away is None):
        raise PreventUpdate
    style_data_conditional_box_score_home = style_data_conditional_box_score(logic.get_max_eff_home())
    style_data_conditional_box_score_away = style_data_conditional_box_score(logic.get_max_eff_away())

    return data_cols, data_home, style_data_conditional_box_score_home, \
           data_cols, data_away, style_data_conditional_box_score_away


###################################

###################################
# efficiency
@app.callback([Output('memory-efficiency-home-data', 'data'),
               Output('memory-efficiency-away-data', 'data')],
              [Input('dropdown-match', 'value')])
def memory_efficiency(str_match_id):
    _return = logic.data_efficiency(int(str_match_id))
    efficiency_home = _return[0]
    efficiency_away = _return[1]
    return efficiency_home, efficiency_away


@app.callback([Output('graph-efficiency-home', 'figure'),
               Output('graph-efficiency-away', 'figure')],
              [Input('memory-efficiency-home-data', 'data'),
               Input('memory-efficiency-away-data', 'data')])
def set_efficiency(data_home, data_away):
    if (data_home is None) | (data_away is None):
        raise PreventUpdate
    return data_home, data_away


###################################

###################################
# assist
@app.callback([Output('memory-assists-data', 'data'),
               Output('memory-assists-starter-bench-data', 'data')],
              [Input('dropdown-match', 'value')])
def memory_assist(str_match_id):
    assist, assist_starter_bench = logic.assist(int(str_match_id))
    return assist, assist_starter_bench


@app.callback([Output('graph-assist', 'figure'),
               Output('stack-graph-assist', 'figure')],
              [Input('memory-assists-data', 'data'),
               Input('memory-assists-starter-bench-data', 'data')])
def set_assist(data_assist, data_assist_starter_bench):
    if (data_assist is None) | (data_assist_starter_bench is None):
        raise PreventUpdate
    return data_assist, data_assist_starter_bench


if __name__ == '__main__':
    app.run_server(debug=True)
