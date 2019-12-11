import pandas as pd
import warnings
from logic.dictionary import Dictionary
from logic.utility import Utility


class Analysis:
    """
    dry_run: if True, do not write to S3
    """
    def __init__(self, match_id, dry_run=True):

        self.__match_id = match_id
        self.__dry_run = dry_run
        self.__utility = Utility(match_id=self.__match_id, dry_run=self.__dry_run)
        self.__dic = Dictionary()

        self.__events = self.__utility.get_events()
        self.__roster = self.__utility.get_roster()
        self.__lov_fouls = self.__utility.LOV_fouls()
        self.__lov_shots = self.__utility.LOV_shots()
        self.__dict_teams = self.__utility.get_team_names()
        self.__home_team = self.__dict_teams['Home']
        self.__away_team = self.__dict_teams['Away']
        self.__dict_id_player = self.__utility.dict_player_fullname()
        self.__shooting_stat_df = self.__utility.get_shooting_stat()
        self.__non_shooting_stat_df = self.__utility.get_non_shooting_stat()
        self.__dict_shot_result_points = self.__dic.shot_result_points

    def match_header(self):
        self.__utility.match_header()

    def point_accumulation(self):
        f_made_shots = (self.__events.MatchEventType == 'Shot') & \
                       (self.__events.ShotResult.isin([200444, 200443, 200442]))  # made shots
        made_shots_df = self.__events.loc[f_made_shots][['MinuteRound', 'ShotResult', 'HomeAway']]
        made_shots_df['PointScored'] = made_shots_df.ShotResult.replace(self.__dict_shot_result_points)
        made_shots_df['MinuteRound'] = made_shots_df.MinuteRound.astype('str')

        end_minute = made_shots_df['MinuteRound'].max() # not always 40 - if overtime
        home_shots_cum_df = made_shots_df.loc[made_shots_df.HomeAway == 'Home'][['MinuteRound', 'PointScored']]
        home_shots_cum_df['CumulativePoints'] = home_shots_cum_df.PointScored.cumsum()
        home_shots_cum_df = home_shots_cum_df[['MinuteRound', 'CumulativePoints']] \
            .groupby('MinuteRound') \
            .agg('max') \
            .reset_index()

        away_shots_cum_df = made_shots_df.loc[made_shots_df.HomeAway == 'Away'][['MinuteRound', 'PointScored']]
        away_shots_cum_df['CumulativePoints'] = away_shots_cum_df.PointScored.cumsum()
        away_shots_cum_df = away_shots_cum_df[['MinuteRound', 'CumulativePoints']] \
            .groupby('MinuteRound') \
            .agg('max') \
            .reset_index()

        dict_home_shots_cum = home_shots_cum_df.to_dict()
        dict_away_shots_cum = away_shots_cum_df.to_dict()

        dict_home_cum_score = {'1900-01-01 00:00:00': 0}
        dict_away_cum_score = {'1900-01-01 00:00:00': 0}
        list_all_minutes = list(pd.Series(
            pd.date_range(start='1900-01-01 00:01:00', end=end_minute, freq='min'))
                                .dt.strftime('%M-%s'))
        home_swapped_dict = dict((v, k) for k, v in dict_home_shots_cum['MinuteRound'].items())
        away_swapped_dict = dict((v, k) for k, v in dict_away_shots_cum['MinuteRound'].items())

        home_score = 0
        away_score = 0
        for minute in list_all_minutes:

            try:
                index = home_swapped_dict[minute]
                home_score = dict_home_shots_cum['CumulativePoints'][index]
                dict_home_cum_score[minute] = home_score
            except:
                dict_home_cum_score[minute] = home_score

            try:
                index = away_swapped_dict[minute]
                away_score = dict_away_shots_cum['CumulativePoints'][index]
                dict_away_cum_score[minute] = away_score
            except:
                dict_away_cum_score[minute] = away_score

        home_cum_score_df = pd.DataFrame.from_dict(dict_home_cum_score, orient='index', columns=['Score']) \
            .reset_index() \
            .rename(columns={'index': 'Minute', 'Score': 'Home'})

        away_cum_score_df = pd.DataFrame.from_dict(dict_away_cum_score, orient='index', columns=['Score']) \
            .reset_index() \
            .rename(columns={'index': 'Minute', 'Score': 'Away'})

        cum_score_df = pd.merge(home_cum_score_df, away_cum_score_df, on="Minute")
        cum_score_df['MinuteRound'] = cum_score_df.Minute.astype(str).str[-5:-3]
        cum_score_df['Difference'] = cum_score_df.Home - cum_score_df.Away  # if positive -> Home leading

        cum_score_df['MatchId'] = self.__match_id
        cum_score_df = cum_score_df.sort_values(by='Minute')
        folder_name = "cumulative_score"
        # return cum_score_df
        self.__utility.save_dataframe(cum_score_df, folder_name)

    def assist(self):
        """
        :return:
        """
        f_assist = (self.__events.Assist != 0)
        columns = ['Assist', 'PeriodName', 'Player', 'ShotResult', 'HomeAway', 'MinuteRound']
        assist_df = self.__events.loc[f_assist][columns]
        assist_df['PlayerId'] = assist_df.Assist
        assist_df['Assist'] = assist_df.Assist.replace(self.__dict_id_player)
        assist_df['Scorer'] = assist_df.Player.replace(self.__dict_id_player)
        assist_df['Point'] = assist_df.ShotResult.replace(self.__dict_shot_result_points)
        assist_df['Team'] = assist_df.HomeAway.replace(self.__dict_teams)
        assist_df['MinuteRound'] = assist_df.MinuteRound.dt.strftime('%M-%s')
        assist_df['Starter'] = assist_df.PlayerId.replace(self.get_starters())
        assist_df['MatchId'] = self.__match_id
        assist_df = assist_df.drop(['ShotResult', 'Player'], axis=1).reset_index(drop=True)

        folder_name = "assists"
        self.__utility.save_dataframe(assist_df, folder_name)
        #return assist_df

    def scoring(self):
        """
        """
        df = self.__utility.get_events()
        f_scorers = df.MatchEventType == 'Shot'
        columns = ['PeriodName', 'Player', 'ShotResult', 'HomeAway', 'MinuteRound']
        df = df.loc[f_scorers][columns]
        df['Scorer'] = df.Player.replace(self.__dict_id_player)
        df['Point'] = df.ShotResult.replace(self.__dict_shot_result_points)
        df['Team'] = df.HomeAway.replace(self.__dict_teams)
        df['ShotDescription'] = df.ShotResult.replace(self.get_shot_description())
        df = df.drop(['Player', 'ShotResult'], axis=1).reset_index(drop=True)
        df['MinuteRound'] = df.MinuteRound.dt.strftime('%M-%s')
        df['MatchId'] = self.__match_id

        #print(df.head(10))
        folder_name = "scoring"
        self.__utility.save_dataframe(df, folder_name)

    def player_statistic(self):
        """
        Efficiency is calculated using Euroleague formula:
        (Points + Rebounds + Assists + Steals + Blocks + Fouls Drawn)
        - (Missed Field Goals + Missed Free Throws + Turnovers + Shots Rejected + Fouls Committed)
        'Fouls Drawn' and 'Shots Rejected' are not in the equation since they are not registered in the play-by-play data
        """
        shooting_stat_df = self.__shooting_stat_df.drop(['PlayerName', 'Team'], axis=1)
        shooting_stat_df = shooting_stat_df.loc[shooting_stat_df.MatchId == self.__match_id]
        shooting_stat_df['Point'] = (shooting_stat_df.Made1 * 1) + (shooting_stat_df.Made2 * 2) + (
                    shooting_stat_df.Made3 * 3)
        shooting_stat_df['MissedShot'] = shooting_stat_df.Missed2 + shooting_stat_df.Missed3
        shooting_stat_df['MissedFreeThrow'] = shooting_stat_df.Missed1

        shooting_stat_df['FTA'] = shooting_stat_df.Missed1 + shooting_stat_df.Made1
        shooting_stat_df['2FGA'] = shooting_stat_df.Missed2 + shooting_stat_df.Made2
        shooting_stat_df['3FGA'] = shooting_stat_df.Missed3 + shooting_stat_df.Made3

        non_shooting_stat_df = self.__non_shooting_stat_df
        non_shooting_stat_df = non_shooting_stat_df.loc[non_shooting_stat_df.MatchId == self.__match_id]
        non_shooting_stat_df['REB'] = non_shooting_stat_df.DefensiveRebound + non_shooting_stat_df.OffensiveRebound

        all_stat_df = pd.DataFrame.merge(shooting_stat_df, non_shooting_stat_df, on=['Player', 'MatchId'])

        all_stat_df['Efficiency'] = (all_stat_df.Point +
                                     all_stat_df['REB'] +
                                     all_stat_df.Assist +
                                     all_stat_df.Steal +
                                     all_stat_df.Block) - \
                                    (all_stat_df.MissedShot +
                                     all_stat_df.MissedFreeThrow +
                                     all_stat_df.Turnover +
                                     all_stat_df.Foul)

        reverse_dict_teams = {value: key for key, value in self.__dict_teams.items()}
        all_stat_df['HomeAway'] = all_stat_df.Team.replace(reverse_dict_teams)

        # starters are read from a dictionary and get a star (*) in front of their name
        all_stat_df['Starter'] = all_stat_df['Player'].replace(self.get_starters()).replace({'Y': '*', 'N': ''})
        all_stat_df['PlayerName'] = all_stat_df.Starter + all_stat_df['PlayerName']

        # Add minutes to the statistics
        df_playtime = self.get_playtime()
        df_playtime = df_playtime[['Player', 'PlayTime']].groupby('Player').sum().reset_index()
        all_stat_df = pd.merge(all_stat_df, df_playtime, on='Player')

        all_stat_df = all_stat_df.rename(columns={'Player': 'PlayerId',
                                                  'PlayerName': 'Player',
                                                  'Point': 'Points',
                                                  'Block': 'BLK',
                                                  'Assist': 'AST',
                                                  'Turnover': 'TOV',
                                                  'Foul': 'FLS',
                                                  'Steal': 'STL',
                                                  'Made1': 'FTM',
                                                  'Made2': '2FGM',
                                                  'Made3': '3FGM',
                                                  'DefensiveRebound': 'DREB',
                                                  'OffensiveRebound': 'OREB',
                                                  'PlayTime': 'MIN'})

        columns = ['MatchId', 'PlayerId', 'HomeAway', 'Team', 'Player', 'MIN', 'Points', '2FGM', '2FGA', '3FGM', '3FGA', 'FTM', 'FTA']
        columns = columns + ['DREB', 'OREB', 'REB', 'AST', 'STL', 'TOV', 'BLK', 'FLS', 'Efficiency', 'Starter']
        all_stat_df = all_stat_df[columns]
        folder_name = "player_stat"
        #print(all_stat_df)
        self.__utility.save_dataframe(all_stat_df, folder_name)
        #return all_stat_df

    def team_fouls_per_period(self):

        list_team_foul_period = []
        for period in self.__dic.period_name_list.keys():
            for ha in self.__dict_teams.keys():
                filter_bonus = (self.__events.MatchEventType == 'Foul') & \
                               (self.__events.HomeAway == ha) & \
                               (self.__events.PeriodName == period)
                out = self.__events.loc[filter_bonus]['PeriodTime'].dropna()
                if out.count() > 3:  # if team commited more than 3 fouls per period
                    l_out = list(out)
                    minute = str(l_out[3])  # get minute of 4th team foul in period
                else:
                    minute = '1900-01-01 00:00:00'
                data = {'Period': period, 'HomeAway': ha, 'NoFouls': out.count(), 'Minute': minute}
                list_team_foul_period.append(data)

        team_foul_period = pd.DataFrame.from_records(list_team_foul_period) \
            .reset_index(drop=True)
        team_foul_period['MatchId'] = self.__match_id
        team_foul_period['TeamName'] = team_foul_period['HomeAway'].replace(self.__dict_teams)
        team_foul_period['NoFouls'] = team_foul_period.NoFouls.astype('int64')
        team_foul_period['Period'] = team_foul_period.Period.astype('int64')

        folder_name = "team_fouls_per_period"
        self.__utility.save_dataframe(team_foul_period, folder_name)

    def run_all_analyses(self):
        self.match_header()
        self.point_accumulation()
        self.assist()
        self.scoring()
        self.player_statistic()
        self.team_fouls_per_period()

    ######
    ## Getters
    ######

    def get_events(self):
        return self.__events

    def get_shot_description(self):
        return self.__dic.shot_description

    def get_home_team(self):
        return self.__home_team

    def get_away_team(self):
        return self.__away_team

    def get_playtime(self):
        return self.__utility.get_all_playtimes()

    def get_starters(self):
        return self.__utility.get_starters()

    def get_all_playtimes(self):
        return self.__utility.get_all_playtimes()

