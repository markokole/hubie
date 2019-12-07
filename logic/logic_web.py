import plotly.graph_objs as go
import boto3
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)


def load_dataframe(folder):
    """
    Load data from all files in a folder to a dataframe
    :param folder: holds files with datasets
    :return: dataframe
    """
    s3 = boto3.resource('s3')
    bucket_name = "hubie"
    bucket = s3.Bucket(bucket_name)
    path = "blno/" + folder
    df = pd.DataFrame()
    for obj in bucket.objects.filter(Prefix=path):
        file_name = obj.key
        if file_name.find('json') != -1:
            obj = s3.Object(bucket_name, file_name)
            body = obj.get()['Body'].read()
            df_tmp = pd.read_json(body, lines=True)
            df = df.append(df_tmp)
    return df


class Logic:
    """
    """

    def __init__(self, str_match_id=7032979, verbose=True):
        """
        Initialize the instance of Logic object
        :param str_match_id: id of the match that is being visualized
        """
        self.__match_id = int(str_match_id)
        self.__verbose = verbose # print out data for debugging
        self.__home_team = ""
        self.__away_team = ""
        self.__max_eff_home = ""
        self.__max_eff_away = ""
        # define columns to display and correct order for Box Score
        self.__cols_box_score = ['Player', 'MIN', 'Points', '2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA']
        self.__cols_box_score = self.__cols_box_score + ['DREB', 'OREB', 'REB', 'AST', 'STL', 'TOV', 'BLK', 'FLS',
                                                         'Efficiency']

        self.__df_match_list = load_dataframe("match_header")
        self.__df_player_stat = load_dataframe("player_stat")
        self.__df_cumulative_score = load_dataframe("cumulative_score")
        self.__df_assist = load_dataframe("assists")

    def write_details(self, text):
        if self.__verbose:
            print(text)


    def match_list(self, league):
        """
        :return:
        """
        df = self.__df_match_list
        filter_league = df.League == league
        df = df.loc[filter_league].sort_values(by='Match Date')
        dict_all_headers = df.to_dict(orient='records')
        all_game_headers = [{'label': "   {}: {} {}:{} {}".format(row['Short Date'], row['HomeTeam'], row['Score Home'],
                                                                  row['Score Away'], row['AwayTeam']),
                             'value': row['MatchId']}
                            for row in dict_all_headers]

        return all_game_headers

    def match_title(self, match_id):
        """
        :param match_id:
        :return:
        """
        df = self.__df_match_list
        f_match_id = (df.MatchId == match_id)
        single_match = df.loc[f_match_id].to_dict(orient='records')[0]
        self.__home_team = single_match['HomeTeam']
        self.__away_team = single_match['AwayTeam']
        home_score = single_match['Score Home']
        away_score = single_match['Score Away']

        title = "   {} {}:{} {}".format(self.__home_team, home_score, away_score, self.__away_team)
        return title

    def all_leagues(self):
        """
        :return: All available leagues in the dataset
        """
        df = self.__df_match_list
        list_leagues = df.League.unique().tolist()
        return list_leagues

    def quarter_score(self, match_id):
        """
        :param match_id:
        :return:
        """
        df = self.__df_cumulative_score
        f_match_id = df.MatchId == match_id
        df = df.loc[f_match_id]
        cols = ['Away', 'Home', 'MinuteRound']
        df = df[cols]
        quarter_end = [10, 20, 30, 40]  # TO-DO: overtime!!!
        last_score_home = 0
        last_score_away = 0
        list_home_quarter_score = []
        list_away_quarter_score = []
        for end in quarter_end:
            f_end_q = df.MinuteRound == end
            _df = df.loc[f_end_q]
            dict_q = _df.to_dict(orient='records')[0]
            score_home = dict_q['Home'] - last_score_home
            score_away = dict_q['Away'] - last_score_away
            list_home_quarter_score.append(score_home)
            list_away_quarter_score.append(score_away)
            last_score_home = dict_q['Home']
            last_score_away = dict_q['Away']

        x_axis = [self.__home_team, self.__away_team]
        list_quarter_score = []  # quartery score for showing in heading
        trace = []  # quarterly scores for showing in graph
        for i in range(0, len(list_home_quarter_score)):
            list_quarter_score.append("{}:{}".format(list_home_quarter_score[i], list_away_quarter_score[i]))
            temp_name_trace = "{}. quarter".format(str(i + 1))
            temp_y_trace = [list_home_quarter_score[i], list_away_quarter_score[i]]

            temp_trace = go.Bar(
                x=x_axis,
                y=temp_y_trace,
                name=temp_name_trace
            )
            trace.append(temp_trace)

        figure_score_per_quarter = {'data': trace,
                                    'layout': go.Layout(
                                        title='Scoring per quarter',
                                        xaxis={'title': 'Team'},
                                        barmode="stack"
                                    )
                                    }

        return '  '.join(list_quarter_score), figure_score_per_quarter

    def starter_bench(self, match_id, statistical_category):
        """
        :param match_id:
        :param statistical_category:
        :return:
        """
        df = self.__df_player_stat
        filter_match = df.MatchId == match_id
        df = df.loc[filter_match]
        the_column = statistical_category
        cols = ['MatchId', 'HomeAway', 'Starter', the_column]
        df = df[cols]
        df['Team'] = df.HomeAway.replace({'Home': self.__home_team, 'Away': self.__away_team})
        df = df.drop(['HomeAway'], axis=1)

        df = df[['Team', 'Starter', the_column]].groupby(['Team', 'Starter']).sum().reset_index()
        df = df.groupby(['Team', 'Starter']).sum().reset_index()

        x_axis = df.Team.unique()
        y_trace1 = df.loc[df.Starter == '*'][the_column].tolist()
        name_trace1 = "Starters"
        y_trace2 = df.loc[df.Starter == ''][the_column].tolist()
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

        figure_stat_cat_starter_bench = {'data': [trace1, trace2],
                                         'layout': go.Layout(
                                             title='{} distribution'.format(the_column),
                                             xaxis={'title': 'Team'},
                                             barmode="stack"
                                         )
                                         }

        return figure_stat_cat_starter_bench

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
        """
        :param match_id:
        :return:
        """
        df = self.__df_player_stat
        f_match = df.MatchId == match_id
        df = df.loc[f_match]

        df = df.copy()
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

        return figure_assist #, figure_assist_starter_bench

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
