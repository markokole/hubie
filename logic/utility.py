from datetime import datetime
from logic.dictionary import Dictionary
import json
import pandas as pd
import boto3
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


class Utility:    
    def __init__(self, match_id=0, dry_run=True):
        
        self.__dic = Dictionary()
        self.__match_id = match_id
        self.__dry_run = dry_run
        self.__s3 = boto3.resource('s3')
        self.__bucket_name = "hubie"
        self.__path_staging_in = "blno/STAGING_IN/"
        self.__path_historical_files = 'blno/HISTORICAL_FILES/'
        self.__bucket = self.__s3.Bucket(self.__bucket_name)

        self.__df_data = pd.DataFrame()
        self.__df_events = pd.DataFrame()
        self.__df_roster = pd.DataFrame()
        self.__df_shooting_stat = pd.DataFrame()
        self.__df_non_shooting_stat = pd.DataFrame()

        if self.__match_id > 0:
            self.__df_summary, self.__home_team, self.__away_team = self.__parse_summary_file()
            self.__df_data = self.__parse_events_file()
            self.__df_events = self.__event(data=self.__df_data)
            self.__df_roster = self.__roster(self.__df_data, self.__home_team, self.__away_team)
            self.__df_shooting_stat = self.__shooting_stat(self.__df_events)
            self.__df_non_shooting_stat = self.__non_shooting_stat(self.__df_events)
            self.__dict_starters, self.__players_all_playtimes = self.__players_all_playtimes(self.__df_events)

    def __parse_summary_file(self):
        """
        :return: dataframe with metadata about match
        """
        summary_file = str(self.__match_id) + "_MatchSummaryViewModel.json"
        print("Processing summary file: {}".format(self.__path_staging_in + summary_file))
        obj = self.__s3.Object(self.__bucket_name, self.__path_staging_in + summary_file)
        body = obj.get()['Body'].read().decode("utf-8")
        data_summary = json.loads(body)
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")

        league = data_summary['Tournament']
        home_team = data_summary['HomeTeam']
        away_team = data_summary['AwayTeam']
        score_home = data_summary['HomeGoals']
        score_away = data_summary['AwayGoals']
        match_date = data_summary['Date'][:10] # get only date
        short_date = match_date[-2:] + "." + match_date[-5:-3] + "." + match_date[2:4]
        periods = data_summary['Periods']
        period_score_home = []
        period_score_away = []

        for i in range(len(periods)):
            period_score_home.append(periods[i]['HomeGoals'])
            period_score_away.append(periods[i]['AwayGoals'])

        match_summary = [[league, self.__match_id, home_team, away_team, match_date, short_date,
                          score_home, score_away, period_score_home, period_score_away, current_time]]

        columns = ['League', 'MatchId', 'HomeTeam', 'AwayTeam', 'Match Date', 'Short Date', 'Score Home', 'Score Away', 'Period Score Home', 'Period Score Away', 'CreatedTime']
        df = pd.DataFrame(data=match_summary, columns=columns)
        return df, home_team, away_team

    def match_header(self):
        folder_name = "match_header"
        print(self.__df_summary[['Match Date', 'HomeTeam', 'AwayTeam']])
        self.save_dataframe(self.__df_summary, folder_name)

    def __parse_events_file(self):
        """
        :return:
        """
        events_file = str(self.__match_id) + "_MatchEventsViewModel.json"
        print("Processing events file: {}".format(self.__path_staging_in + events_file))
        obj = self.__s3.Object(self.__bucket_name, self.__path_staging_in + events_file)
        body = obj.get()['Body'].read().decode("utf-8")
        data = json.loads(body)

        '''self.events = self.__event()
        self.roster = self.__roster()
        self.shooting_stat = self.__shooting_stat()
        self.non_shooting_stat = self.__non_shooting_stat()
        self.dict_starters, self.players_all_playtimes = self.__players_all_playtimes()'''
#        self.event_lineups = self.__event_lineups()
        return data

######
## Prepare dataframes
######    
    
    def __roster(self, data, home_team, away_team):
        home_players = data['HomePlayers']
        away_players = data['AwayPlayers']

        for player in home_players:
            player['HomeAway'] = 'H'
            player['Team'] = home_team
        for player in away_players:
            player['HomeAway'] = 'A'
            player['Team'] = away_team

        players_full_list = home_players + away_players
        players_full = pd.DataFrame.from_records(players_full_list, exclude=['IsCaptain', 'IsCoach'])
        players_full = players_full.loc[players_full.ShirtNo.notnull()] # SihrtNo=None is coaching staff

        return players_full

    def __event(self, data):
        """
        """
        events = pd.DataFrame(data['Events']).fillna(0) # text replacement
        events = events.loc[events.PeriodTime != ''] # remove rows with no time
        events['Team'] = events['Team'].replace({'B': 'Away', 'H': 'Home'}) #change norwegian B (Borte) with english A (Away)

        # type conversion
        convert_cols = ['Assist', 'Player', 'PlayerIn', 'PlayerOut', 'ShotResult', 'FoulType']
        events[convert_cols] = events[convert_cols].apply(lambda x: x.astype('int32'))

        #format PeriodTime column
        events['PeriodTime'] = pd.to_datetime(events.PeriodTime, format='%M:%S')
        events = events.rename(columns={'Team': 'HomeAway'})
        # Creates column Minute which hold time values from 00:00:00 to 00:50:00
        dict_period_to_minute = {'1. periode': 0, '2. periode': 10, '3. periode': 20, '4. periode': 30,
                                 '1. ekstraomgang': 40, '2. ekstraomgang': 45, '3. ekstraomgang': 50}

        events['Minute'] = events.PeriodName.replace(dict_period_to_minute)
        events['Minute'] = pd.to_timedelta(events.Minute, unit='m')
        events['Minute'] = events['Minute'] + events['PeriodTime']

        # Round up to a full minute for aggregation
        events['MinuteRound'] = events.Minute.dt.ceil(freq="min")

        # Some play-by-play datasets begin with MatchEventType = Substitution. Those rows are removed here
        filter_sub_first = (events.MatchEventType == 'Substitution') & (events.Minute == pd.to_datetime('1900-01-01 00:00:00'))
        no_top_sub_rows = len(events.loc[filter_sub_first])
        events = events[no_top_sub_rows:]
        events.index = range(len(events))

        return events

    def __players_all_playtimes(self, events):
        """
        Method calculates each player's time on the floor - every time interval the player is on the floor
        Return: DataFrame with following columns: HomeAway Player In Out PlayTime
        """

        dict_players = self.dict_player_fullname()
        #dict_player_team = self.dict_player_team()

        #cols = ['PlayerIn', 'PlayerOut', 'Minute']
        df_subs = events.loc[events.MatchEventType == 'Substitution']

        first_second = [pd.to_datetime('1900-01-01 00:00:00')]
        last_second = [pd.to_datetime('1900-01-01 00:40:00')]
        playing_time = []
        dict_starters = {}

        for player_id, name in dict_players.items():
            in_out = []
            list_minutes = []
            list_playing_time = []
            f_sub = (df_subs.PlayerIn == player_id) | (df_subs.PlayerOut == player_id)
            df_subs_player = df_subs.loc[f_sub].reset_index(drop=True)

            if not df_subs_player.empty:  # only players that were substituted.
                for idx in range(len(df_subs_player)):
                    row = df_subs_player.iloc[idx]
                    list_minutes.append(row['Minute'])
                    if row['PlayerIn'] == player_id:
                        in_out.append('in')
                    if row['PlayerOut'] == player_id:
                        in_out.append('out')

                # if starter add first_second at the beginning
                if in_out[0] == 'out':
                    in_out = ['in'] + in_out
                    list_minutes = first_second + list_minutes
                    dict_starters[player_id] = 'Y'
                else:
                    dict_starters[player_id] = 'N'

                # if finished game add last_second at the end
                if in_out[-1] == 'in':
                    in_out = in_out + ['out']
                    list_minutes = list_minutes + last_second

                for idx in range(len(in_out) - 1, 0, -2):  # go backwards and loop only through 'out' values
                    delta_time = list_minutes[idx] - list_minutes[idx - 1]
                    list_playing_time.append(delta_time)
                    playing_time.append(
                        {'player_id': player_id, 'in': list_minutes[idx-1], 'out': list_minutes[idx]})

        list_players_in_sub = df_subs.PlayerIn.tolist() + df_subs.PlayerOut.tolist() # all players in substitution
        all_players = dict_players.keys() # all players
        not_in_sub = all_players - list_players_in_sub  # players not in substitution column

        for player_id in not_in_sub:
            _count = events['Player'].loc[events.Player.isin([player_id])].count()
            if _count > 0:  # player played all game
                playing_time.append({'player_id': player_id, 'in': pd.to_datetime(first_second[0]), 'out': pd.to_datetime(last_second[0])})
                dict_starters[player_id] = 'Y'
            else:  # player didnt play
                playing_time.append({'player_id': player_id, 'in': pd.to_datetime(first_second[0]), 'out': pd.to_datetime(first_second[0])})
                dict_starters[player_id] = 'N'

        df_play_time = pd.DataFrame.from_records(playing_time)
        df_play_time.columns = ['In', 'Out', 'Player']
        df_play_time['PlayTime'] = df_play_time.Out - df_play_time.In
        df_play_time['MatchId'] = self.__match_id
        df_play_time = df_play_time[['MatchId', 'Player', 'In', 'Out', 'PlayTime']]
        return dict_starters, df_play_time

    def __event_lineups(self):
        """
        Calculates the lineups for home and away teams at each registered event
        """
        
        list_events_minutes = self.events.Minute.loc[self.events.MatchEventType != 'Substitution'].unique()
        list_lineups_at_event = []
        playtime_df = self.players_all_playtimes
        for t in list_events_minutes:
            f = (playtime_df.In < t) & \
                (playtime_df.Out >= t)

            home_list = playtime_df['Player'].loc[f & (playtime_df.HomeAway == 'Home')].tolist()
            away_list = playtime_df['Player'].loc[f & (playtime_df.HomeAway == 'Away')].tolist()

            dict_home_lineup = {"Minute": pd.to_datetime(t), "Lineup": home_list, "HomeAway": "Home"}
            dict_away_lineup = {"Minute": pd.to_datetime(t), "Lineup": away_list, "HomeAway": "Away"}

            list_lineups_at_event.append(dict_home_lineup)
            list_lineups_at_event.append(dict_away_lineup)

            list_events_players = []
            for line in list_lineups_at_event:
                for player_id in line['Lineup']:
                    row = {'Minute': line['Minute'], 'Player': player_id, 'HomeAway': line['HomeAway']}
                    list_events_players.append(row)

        event_lineups_df = pd.DataFrame.from_records(list_events_players)
        event_lineups_df['MatchId'] = self.__match_id
        return event_lineups_df
    
    def event_lineups_oneline(self):
        """
        Return DataFrame with one line per event per Home/Away team with a Minute of one event and a comma separated string with 5 PlayerIds
        """
        distinct_minute = self.event_lineups.Minute.unique() # Minute of every event
        list_all_rows = [] # temp list
        for minute in distinct_minute: 
            for ha in self.dict_team_names().keys(): # iterate for Home and Away
                f_homeaway = (self.event_lineups.HomeAway == ha) & (self.event_lineups.Minute == minute)
                str_event_lineup = ','.join(str(e) for e in list(self.event_lineups.Player.loc[f_homeaway])) 

                row = {"Minute": pd.to_datetime(minute), "Lineup": str_event_lineup, "HomeAway": ha}
                list_all_rows.append(row)
        df_lineup_event = pd.DataFrame.from_records(list_all_rows)

        return df_lineup_event

    def __shooting_stat(self, events):
        """
        """
        df = events[['Player', 'ShotResult', 'MatchEventType']]
        f = (df.MatchEventType == 'Shot')
        df = df.loc[f][['ShotResult', 'Player']]
        
        list_all_rows = []
        for player_id in self.dict_player_fullname().keys(): #loop through all players 
            for shot in self.__dic.shot_description: #loop through all shot types
                f = (df.ShotResult == shot) & (df.Player == player_id)
                try: # if no attempt made, value with index 1 is null
                    count_shot = f.value_counts()[1]
                except KeyError:
                    count_shot = 0
                if shot == 200443: made2 = count_shot
                if shot == 200581: missed2 = count_shot
                if shot == 200444: made1 = count_shot
                if shot == 200445: missed1 = count_shot
                if shot == 200442: made3 = count_shot
                if shot == 200580: missed3 = count_shot
            row = [player_id, made2, missed2, made1, missed1, made3, missed3]
            list_all_rows.append(row)
        shot_df = pd.DataFrame.from_records(list_all_rows, columns=["Player", "Made2", "Missed2", "Made1", "Missed1", "Made3", "Missed3"])
        shot_df['PlayerName'] = shot_df.Player.replace(self.dict_player_fullname())
        shot_df['Team'] = shot_df.Player.replace(self.dict_player_team())
        shot_df['MatchId'] = self.__match_id
        return shot_df

    def __assist_stat(self, events):
        """
        Return DataFrame with Player Id and sum of all assists
        
        Because assists are stored in separate column in the source files, this method is needed.
        """
        df = events
        f_assist = (df.Assist != 0)
        df = df[['Player', 'Assist']].loc[f_assist].groupby('Assist').count().reset_index()
        list_assist = []
        for player_id in self.dict_player_fullname().keys():
            no_assists = 0
            f = (df.Assist == player_id)
            if (f.sum() == 1):
                no_assists = (list(df.loc[f]['Player'])[0])
                
            assist = [player_id, no_assists]
            list_assist.append(assist)

        assist_df = pd.DataFrame.from_records(list_assist, columns=['Player', 'Assist'])
        return assist_df

    def __foul_stat(self):
        """
        Return DataFrame with Player Id and sum of all fouls
        Because fouls are stored in separate column in the source files, this method is needed.
        """
        df = self.__df_events
        f_foul = (df.FoulType != 0)
        df = df[['Player', 'FoulType']].loc[f_foul].groupby('Player').count().reset_index()

        list_foul = []
        for player_id in self.dict_player_fullname().keys():
            no_fouls = 0
            f = (df.Player == player_id)
            if f.sum() == 1:
                no_fouls = (list(df.loc[f]['FoulType'])[0])
                
            foul = [player_id, no_fouls]
            list_foul.append(foul)

        foul_df = pd.DataFrame.from_records(list_foul, columns=['Player', 'Foul'])
        return foul_df

    def __non_shooting_stat(self, events):
        """
        """
        df = events
        event_type = ['DefensiveRebound', 'OffensiveRebound', 'Turnover', 'Steal', 'Block']
        f = (df.MatchEventType.isin(event_type))
        columns = ['Player', 'MatchEventType', 'HomeAway', 'PeriodTime']
        df = df[columns].loc[f]

        list_all_rows = []
        for player_id in self.dict_player_fullname().keys():
            for event in event_type:        
                f = (df.MatchEventType == event) & (df.Player == player_id)
                try: # if no stat for this event, value with index 1 is null
                    count_event = f.value_counts()[1]
                except KeyError:
                    count_event = 0

                if event == 'DefensiveRebound': def_reb = count_event
                if event == 'OffensiveRebound': off_reb = count_event
                if event == 'Turnover': turnover = count_event
                if event == 'Steal': steal = count_event
                if event == 'Block': block = count_event

            row = [player_id, def_reb, off_reb, turnover, steal, block]
            list_all_rows.append(row)
        non_shot_df = pd.DataFrame.from_records(list_all_rows, columns= ['Player'] + event_type) # columns are all event types
        non_shot_df['PlayerName'] = non_shot_df.Player.replace(self.dict_player_fullname())
        non_shot_df['Team'] = non_shot_df.Player.replace(self.dict_player_team())
        non_shot_df['MatchId'] = self.__match_id
        
        all_non_shot_stat_df = pd.DataFrame.merge(non_shot_df, self.__assist_stat(events)) # join to get assists data
        all_non_shot_stat_df2 = pd.DataFrame.merge(all_non_shot_stat_df, self.__foul_stat()) # join to get fouls data

        return all_non_shot_stat_df2

        
######
# Getters
######

    def get_events(self):
        return self.__df_events

    def get_roster(self):
        return self.__df_roster

    def get_shooting_stat(self):
        return self.__df_shooting_stat

    def get_non_shooting_stat(self):
        return self.__df_non_shooting_stat

    def get_match_summary(self):
        return self.__df_summary

    def get_starters(self):
        return self.__dict_starters

    def get_all_playtimes(self):
        return self.__players_all_playtimes

    def get_team_names(self):
        return {"Home": self.__home_team, "Away": self.__away_team}

######
## List of values
######
    
    def LOV_fouls(self):
        LOV_fouls = pd.DataFrame(self.__df_events.FoulType.astype('str').unique(), columns=['FoulType'])
        LOV_fouls['FoulTypeDesc'] = LOV_fouls.replace(self.__dic.foul_description)
        return LOV_fouls
        
    def LOV_shots(self):
        LOV_shots = pd.DataFrame(self.__df_events.ShotResult.unique(), columns=['ShotResult'])
        LOV_shots['ShotResultDesc'] = LOV_shots.replace(self.__dic.shot_description)
        return LOV_shots

    def dict_player_fullname(self):
        player_full_df = self.__df_roster
        player_fullname_df = pd.DataFrame(player_full_df.FirstName + ' ' + player_full_df.LastName, columns=['FullName'])
        player_fullname_df.index = player_full_df.Id
        dict_player_fullname = player_fullname_df.to_dict()['FullName']
        return dict_player_fullname
    
    def dict_player_team(self):
        player_full_df = self.__df_roster
        player_team_df = player_full_df['Team']
        player_team_df.index = player_full_df.Id
        player_team_df.column = ['Team']
        dict_player_team = player_team_df.to_dict()
        return dict_player_team

######
# Save to S3
######

    def save_dataframe(self, df, folder_name):
        if self.__dry_run != True:
            self.__save_dataframe_s3(df=df, folder=folder_name)
            print("Dataframe saved to folder {}.".format(folder_name))
        else:
            print("Dry run is activated: dataframe {} was created but not saved!".format(folder_name))

    def __save_dataframe_s3(self, df, folder):
        competition = 'blno/' + folder + '/'
        s3_resource = boto3.resource('s3')
        bucket_name = 'hubie'
        json_data = df.to_json(force_ascii=False, date_format='iso', orient='records', lines=True)

        s3object = s3_resource.Object(bucket_name, competition + str(self.__match_id) + '.json')

        s3object.put(
            Body=(bytes(json_data.encode('UTF-8')))
        )

