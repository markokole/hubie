# -*- coding: utf-8 -*-
from logic.logic_web import Logic
from dash.dependencies import Input, Output
import dash
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import warnings

#warnings.simplefilter(action='ignore', category=FutureWarning)

logic = Logic(verbose=False)

# Text for explaining Box Score tab
box_score_star_text = "* - player is starter."
efficiency_explanation_text1 = """Efficiency is calculated using Euroleague formula:"""
efficiency_explanation_text2 = """(Points + Rebounds + Assists + Steals + Blocks + Fouls Drawn)
        - (Missed Field Goals + Missed Free Throws + Turnovers + Shots Rejected + Fouls Committed)"""
efficiency_explanation_text3 = """'Fouls Drawn' and 'Shots Rejected' are not in the equation since they are not registered in the play-by-play data."""

efficiency_explanation = html.Div([html.P(children=efficiency_explanation_text1),
                                   html.B(children=efficiency_explanation_text2),
                                   html.P(children=efficiency_explanation_text3)])

style_header_box_score = {'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'}

# dict removes the toolbar that pops up on hover on each graph
remove_toolbar_buttons = {'modeBarButtonsToRemove':
                              ['pan2d', 'lasso2d', 'zoom2d', 'select2d',
                               'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d',
                               'hoverClosestCartesian', 'hoverCompareCartesian',
                               'toggleHover', 'toImage', 'toggleSpikelines'],
                          'displaylogo': False}


def style_data_conditional_box_score(max_eff):
    list_style_data_conditional_box_score = [
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
    list_style_data_conditional_box_score.append(condition_max_eff_home)
    return list_style_data_conditional_box_score


leagues = logic.all_leagues()  # ['BLNO Kvinner Grunnserie']#, 'BLNO Menn Grunnserie']

#######
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = 'Hubie'
app.layout = html.Div([html.Div([dcc.Store(id='memory-title'),
                                 dcc.Store(id='memory-quarter-score'),
                                 dcc.Store(id='memory-cumulative-score-data'),
                                 dcc.Store(id='memory-difference-data'),
                                 dcc.Store(id='memory-score-starter-bench-data'),
                                 dcc.Store(id='memory-score-per-quarter-data'),
                                 dcc.Store(id='memory-box-score-columns'),
                                 dcc.Store(id='memory-box-score-home-data'),
                                 dcc.Store(id='memory-box-score-away-data'),
                                 dcc.Store(id='memory-efficiency-home-data'),
                                 dcc.Store(id='memory-efficiency-away-data'),
                                 dcc.Store(id='memory-assists-data'),
                                 dcc.Store(id='memory-assists-starter-bench-data'),
                                 # left split
                                 html.Div([
                                     html.H4(children='Pick a league:'),
                                     dcc.RadioItems(
                                         id='league-dropdown',
                                         options=[{'label': k, 'value': k} for k in leagues],
                                         value=leagues[0]
                                     ),
                                     html.Br(),
                                     html.H6(children='Pick a match:'),
                                     dcc.RadioItems(id='match-dropdown'),
                                     dcc.Dropdown(id='dropdown-match',
                                                  options=logic.match_list(leagues[0]),
                                                  style={'width': '70%',
                                                         'display': 'inline-block'}
                                                  )
                                 ])
                                 ],
                                className="split left"),
                       # right split
                       html.Div([html.H2(id="h2-title"),
                                 html.H5(id="h5-quarter-score"),
                                 # tabs
                                 dcc.Tabs(id="tabs",
                                          value='tab-scoring',
                                          # scoring
                                          children=[dcc.Tab(label='Scoring',
                                                            value='tab-scoring',
                                                            children=[html.Div(
                                                                [html.Div(dcc.Graph(id='graph-cumulative-score',
                                                                                    config=remove_toolbar_buttons),
                                                                          className="div graph"),
                                                                 html.Br(),
                                                                 html.Div(dcc.Graph(id='graph-difference',
                                                                                    config=remove_toolbar_buttons),
                                                                          className="div graph"),
                                                                 html.Div([html.Div(dcc.Graph(
                                                                     id='graph-score-starter-bench',
                                                                     config=remove_toolbar_buttons),
                                                                     className="six columns div graph"),
                                                                     html.Div(dcc.Graph(id="graph-score-per-quarter",
                                                                                        config=remove_toolbar_buttons),
                                                                              className="six columns div graph")])],
                                                                className="row"
                                                            )]
                                                            ),
                                                    # box score
                                                    dcc.Tab(label='Box Score',
                                                            value='tab-box-score',
                                                            children=[html.P(children=box_score_star_text),
                                                                      efficiency_explanation,
                                                                      dcc.Tabs(id="tabs-box-score",
                                                                               value="tab-box-score-home",
                                                                               children=[
                                                                                   dcc.Tab(
                                                                                       id="tab-box-score-title-home",
                                                                                       value="tab-box-score-home",
                                                                                       children=[html.Br(),
                                                                                                 dash_table.DataTable(
                                                                                                     id='table-box-score-home',
                                                                                                     style_header=style_header_box_score)]),
                                                                                   dcc.Tab(
                                                                                       id="tab-box-score-title-away",
                                                                                       value="tab-box-score-away",
                                                                                       children=[html.Br(),
                                                                                                 dash_table.DataTable(
                                                                                                     id='table-box-score-away',
                                                                                                     style_header=style_header_box_score)
                                                                                                 ])]),
                                                                      html.Br(),
                                                                      html.Br()]
                                                            ),
                                                    # efficiency
                                                    dcc.Tab(label='Efficiency',
                                                            value='tab-efficiency',
                                                            children=[html.Div([html.Div([html.Br(),
                                                                                          dcc.Graph(id='graph-efficiency-home',
                                                                                                    config=remove_toolbar_buttons
                                                                                          )]
                                                                                         ,
                                                                                         className="six columns div graph"),
                                                                                html.Div([html.Br(),
                                                                                          dcc.Graph(id='graph-efficiency-away',
                                                                                                    config=remove_toolbar_buttons
                                                                                          )]
                                                                                         ,
                                                                                         className="six columns div graph")
                                                                                ],
                                                                               className="row")]
                                                            ),
                                                    dcc.Tab(label='Assist',
                                                            value='tab-assist',
                                                            children=[html.Br(),
                                                                      html.Div([
                                                                          html.Div(dcc.Graph(id='graph-assist',
                                                                                             config=remove_toolbar_buttons)
                                                                                   , className="six columns div graph"),
                                                                          html.Div(
                                                                              dcc.Graph(id='graph-assist-starter-bench',
                                                                                        config=remove_toolbar_buttons)
                                                                              , className="six columns div graph"),
                                                                      ], className="row")]
                                                            ),
                                                    dcc.Tab(label='Rebound',
                                                            value='tab-rebound')
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
    logic.write_details("League: " + selected_league)
    return logic.match_list(selected_league)


@app.callback(
    Output('dropdown-match', 'value'),
    [Input('dropdown-match', 'options')])
def set_match_value(leagues):
    return leagues[0]['value']


###################################

###################################
# Match title
@app.callback([Output('memory-title', 'data'),
               Output('memory-quarter-score', 'data'),
               Output('tab-box-score-title-home', 'label'),
               Output('tab-box-score-title-away', 'label')],
              [Input('dropdown-match', 'value')])
def memory_title(str_match_id):
    title = logic.match_title(int(str_match_id))
    title_home = logic.get_home_team()
    title_away = logic.get_away_team()
    quarter_score, dummy = logic.quarter_score(int(str_match_id))
    return title, quarter_score, title_home, title_away


@app.callback([Output('h2-title', 'children'),
               Output('h5-quarter-score', 'children')],
              [Input('memory-title', 'data'),
               Input('memory-quarter-score', 'data')])
def set_h1_title(title_data, quarter_score_data):
    if (title_data is None) | (quarter_score_data is None):
        raise PreventUpdate
    return title_data, quarter_score_data


###################################

###################################
# cumulative score
@app.callback([Output('memory-cumulative-score-data', 'data'),
               Output('memory-difference-data', 'data'),
               Output('memory-score-starter-bench-data', 'data'),
               Output('memory-score-per-quarter-data', 'data')],
              [Input('dropdown-match', 'value')])
def memory_scoring(str_match_id):
    _return_cumulative_score, _return_difference = logic.cumulative_score(int(str_match_id))
    _return_score_starter_bench = logic.starter_bench(int(str_match_id), 'Points')
    quarter_score, _return_score_per_quarter = logic.quarter_score(int(str_match_id))
    return _return_cumulative_score, _return_difference, _return_score_starter_bench, _return_score_per_quarter


@app.callback([Output('graph-cumulative-score', 'figure'),
               Output('graph-difference', 'figure'),
               Output('graph-score-starter-bench', 'figure'),
               Output('graph-score-per-quarter', 'figure')],
              [Input('memory-cumulative-score-data', 'data'),
               Input('memory-difference-data', 'data'),
               Input('memory-score-starter-bench-data', 'data'),
               Input('memory-score-per-quarter-data', 'data')])
def tab_scoring(data_cum_score, data_difference, data_score_starter_bench, data_score_per_quarter):
    if (data_cum_score is None) | (data_difference is None) | (data_score_starter_bench is None) | (
            data_score_per_quarter is None):
        raise PreventUpdate
    return data_cum_score, data_difference, data_score_starter_bench, data_score_per_quarter


###################################


###################################
# box-score
@app.callback([Output('memory-box-score-columns', 'data'),
               Output('memory-box-score-home-data', 'data'),
               Output('memory-box-score-away-data', 'data')],
              [Input('dropdown-match', 'value')])
def memory_box_score(match_id):
    logic.write_details("MatchId: " + str(match_id))
    return_cols = logic.get_box_score_cols()
    return_data_home, return_data_away = logic.box_score(match_id)
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
    logic.write_details("style_data_conditional_box_score_home -> " + str(style_data_conditional_box_score_home))
    logic.write_details("style_data_conditional_box_score_away -> " + str(style_data_conditional_box_score_away))

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
    logic.write_details("efficiency home -> " + str(efficiency_home))
    logic.write_details("efficiency away -> " + str(efficiency_away))
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
    assist = logic.assist(int(str_match_id))
    assist_starter_bench = logic.starter_bench(int(str_match_id), 'AST')
    logic.write_details("assist_starter_bench -> " + str(assist_starter_bench))
    return assist, assist_starter_bench


@app.callback([Output('graph-assist', 'figure'),
               Output('graph-assist-starter-bench', 'figure')],
              [Input('memory-assists-data', 'data'),
               Input('memory-assists-starter-bench-data', 'data')])
def set_assist(data_assist, data_assist_starter_bench):
    if (data_assist is None) | (data_assist_starter_bench is None):
        raise PreventUpdate
    # print(data_assist)
    return data_assist, data_assist_starter_bench  # data_assist, {} #data_assist_starter_bench


if __name__ == '__main__':
    app.run_server(debug=True)
