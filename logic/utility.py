import json
import pandas as pd
import requests
import numpy as np
from datetime import timedelta
import boto3
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from logic.dictionary import Dictionary

class Utility:    
    def __init__(self, events_file=""):
        
        self.__dic = Dictionary()
        self.__events_file = events_file
        
        self.__s3 = boto3.resource('s3')
        self.__bucket_name = "hubie"
        self.__path_staging_in = "blno/STAGING_IN/"
        self.__path_historical_files = 'blno/HISTORICAL_FILES/'
        
        self.__bucket = self.__s3.Bucket(self.__bucket_name)
        self.__obj = self.__s3.Object(self.__bucket_name, self.__path_staging_in + self.__events_file)
        self.__body = self.__obj.get()['Body'].read().decode("utf-8")
        
        self.data_events = ""
        
        if self.__events_file != "":
        
            print("Processing events file: {}".format(self.__path_staging_in + self.__events_file))
            if self.__events_file.find("Events") != -1:
                self.__data = json.loads(self.__body)
                self.data_events = self.__data
                self.home_team = self.__data['HomeTeam']
                self.away_team = self.__data['AwayTeam']

                self.match_id = ''.join([c for c in self.__events_file if c.isdigit()])
                self.events = self.__event()
                self.roster = self.__roster()
                self.shooting_stat = self.__shooting_stat()
                self.non_shooting_stat = self.__non_shooting_stat()
                self.players_all_playtimes = self.__players_all_playtimes()
                self.event_lineups = self.__event_lineups()
            else:
                print("Invalid file: " + self.__events_file + ". Expected an Events file.")
    
######
## Load DataFrames
###### 

    def load_dataframe(self, name):
        #s3_resource = boto3.resource('s3')
        #bucket_name = "hubie"
        self.__name = name
        path = "blno/" + self.__name
        #bucket = s3_resource.Bucket(bucket_name)
        df = pd.DataFrame()
        for obj in self.__bucket.objects.filter(Prefix=path):
            file_name = obj.key
            if file_name.find('json') != -1:
                #print(file_name)
                obj = self.__s3.Object(self.__bucket_name, file_name)
                body = obj.get()['Body'].read()
                #print(body)
                df_tmp = pd.read_json(body, lines=True)
                #print(df_tmp)
                df = df.append(df_tmp)
        
        return df
    
######
## Load data
######   
    '''
        def __load_files(self):
            """
            Loads all files in a dictionary. key: file path, value: file body
            """
            events_files = {}
            summary_files = {} # TO-DO
            for obj in self.__bucket.objects.filter(Prefix=self.__path_staging_in):
                file_name = obj.key
                if file_name.find('Event') != -1:
                    obj = self.__s3.Object(self.__bucket_name, file_name)
                    body = obj.get()['Body'].read()
                    events_files[file_name] = body.decode("utf-8")
            print("Number of Events files loaded: {}.".format(len(events_files)))

            return events_files, summary_files

        def move_file(self, file_name):
            """
            """
            self.s3.Object(self.__bucket_name, self.__path_historical_files + file_name). \
                copy_from(CopySource=self.__bucket_name + self.__path_staging_in + file_name)    
    '''

######
## Prepare dataframes
######    
    
    def __roster(self):
        players_full_list = []
        home_players = self.__data['HomePlayers']
        away_players = self.__data['AwayPlayers']

        for player in home_players:
            player['HomeAway'] = 'H'
            player['Team'] = self.home_team
        for player in away_players:
            player['HomeAway'] = 'A'
            player['Team'] = self.away_team

        players_full_list = home_players + away_players
        players_full = pd.DataFrame.from_records(players_full_list, exclude=['IsCaptain', 'IsCoach'])
        players_full = players_full.loc[players_full.ShirtNo.notnull()] # SihrtNo=None is coaching staff

        return players_full
    
    
    def __event(self):
        """
        """
        events = pd.DataFrame(self.__data['Events']).fillna(0) # text replacement
                
        events = events.loc[events.PeriodTime != ''] # remove rows with no time
        
        events['PeriodName'] = events['PeriodName'].str.replace('. periode', '') # remove .periode
        # events['Team'] = events['Team'].str.replace('B', 'Away') #change norwegian B (Borte) with english A (Away)
        events['Team'] = events['Team'].replace({'B': 'Away', 'H': 'Home'})
        
        # type conversion
        convert_cols = ['Assist', 'Player', 'PlayerIn', 'PlayerOut', 'ShotResult', 'PeriodName', 'FoulType']
        events[convert_cols] = events[convert_cols].apply(lambda x: x.astype('int32'))

        #format PeriodTime column
        #events['OriginalPeriodTime'] = events['PeriodTime']
        events['PeriodTime'] = pd.to_datetime(events.PeriodTime, format='%M:%S')
        events = events.rename(columns={'Team': 'HomeAway'})

        # Creates column Minute which hold time values from 00:00:00 to 00:40:00
        events['Minute'] = 10 * (events['PeriodName'] - 1)
        events['Minute'] = pd.to_timedelta(events.Minute, unit='m')
        events['Minute'] = events['Minute'] + events['PeriodTime']
        
        # Round up to a full minute for aggregation
        events['MinuteRound'] = events.Minute.dt.ceil(freq="min")
        
        # Some play-by-play datasets begin with MatchEventType = Substitution. Those rows are removed here
        filter_sub_first = (events.MatchEventType == 'Substitution') & (events.Minute == pd.to_datetime('1900-01-01 00:00:00'))
        no_top_sub_rows = len(events.loc[filter_sub_first])
        events = events[no_top_sub_rows:]
        events.index = range(len(events))

        self.events = events
        return self.events
    
    
    def __players_all_playtimes(self):
        """
        Method calculates each player's time on the floor - every time interval the player is on the floor
        
        Return: DataFrame with following columns: HomeAway Player In Out PlayTime
        """
        global_sub_inout = pd.DataFrame() # all substitutions - one per row
        global_play_interval = pd.DataFrame() # all substitutions - in&out per row
        global_play_interval_list = []
        
        list_player_ids = self.dict_player_fullname() # unique players' IDs and full name
        for player_id in list_player_ids.keys():

            # get rows where player was involved in a substitution
            filter_substitution = (self.events.MatchEventType == 'Substitution') \
                                & ((self.events.PlayerIn == player_id) | (self.events.PlayerOut == player_id))
            sub_player = self.events[['Minute', 'PlayerIn', 'PlayerOut', 'HomeAway']].loc[filter_substitution]

            if not sub_player.empty: # needed in case player was on the roster but didnt play

                # add time delta from previous row
                sub_player['Difference'] = np.where(sub_player.HomeAway == sub_player.HomeAway.shift(), sub_player.Minute - sub_player.Minute.shift(), np.nan)

                # put PlayerIn and PlayerOut columns into one column and create an InOut column
                sub_in = sub_player[['PlayerIn', 'Minute', 'HomeAway']]
                sub_in = sub_in.rename(columns={"PlayerIn": "Player"})
                sub_in['InOut'] = 'In'

                sub_out = sub_player[['PlayerOut', 'Minute', 'HomeAway']]
                sub_out = sub_out.rename(columns={"PlayerOut": "Player"})
                sub_out['InOut'] = 'Out'

                sub_inout = sub_in.append(sub_out, ignore_index=True) # append together In and Out dataframes
                sub_inout = sub_inout.loc[sub_inout.Player == player_id] # take out only rows with player_id in question

                sub_inout = sub_inout.sort_values(['Minute']) # sort by minutes - needed to check what first and last row status is
                sub_inout.index = range(len(sub_inout)) # recreate index

                home_away = sub_inout.loc[sub_inout.Player == player_id]['HomeAway'][0]

                # if last row is In, means player finished the game
                last_in = list(sub_inout[-1:]['InOut'].isin(['In']))[0]
                if last_in == True:
                    last_row = pd.DataFrame([[home_away, pd.to_datetime('1900-01-01 00:40:00'), player_id, 'Out']], columns=['HomeAway', 'Minute', 'Player', 'InOut'])
                    sub_inout = sub_inout.append(last_row, ignore_index=True)

                # if first row is Out, means player started the game
                first_out = list(sub_inout[:1]['InOut'].isin(['Out']))[0]
                if first_out == True:
                    #starter = 'Y'
                    first_row = pd.DataFrame([[home_away, pd.to_datetime('1900-01-01 00:00:00'), player_id, 'In']], columns=['HomeAway', 'Minute', 'Player', 'InOut'])
                    sub_inout = sub_inout.append(first_row, ignore_index=True)        

                sub_inout = sub_inout.sort_values(['Minute'])
                sub_inout.index = range(len(sub_inout))
                global_sub_inout = global_sub_inout.append(sub_inout)

                # calculate playing time
                play_time = list()
                for i in range(len(sub_inout)): # loop thorugh all Substitutions

                    if sub_inout.iloc[i]['InOut'] == 'Out':
                        global_play_interval_list.append([home_away, player_id, sub_inout.iloc[i-1]['Minute'], sub_inout.iloc[i]['Minute']])

            else: # player didnt play
                global_play_interval_list.append([home_away, player_id, pd.to_datetime('NaT'), pd.to_datetime('NaT')])

        global_play_interval = pd.DataFrame.from_records(global_play_interval_list, columns=['HomeAway', 'Player', 'In', 'Out'])
        global_play_interval['PlayTime'] = global_play_interval.Out - global_play_interval.In
        global_play_interval['MatchId'] = self.match_id
        
        return global_play_interval
    
    
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
        event_lineups_df['MatchId'] = self.match_id
        
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


    def __shooting_stat(self):
        """
        """
        df = self.events[['Player', 'ShotResult', 'MatchEventType']]
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
        shot_df['MatchId'] = self.match_id
        return shot_df
        
    
    def __assist_stat(self):
        """
        Return DataFrame with Player Id and sum of all assists
        
        Because assists are stored in separate column in the source files, this method is needed.
        """
        df = self.events
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
        df = self.events
        f_foul = (df.FoulType != 0)
        df = df[['Player', 'FoulType']].loc[f_foul].groupby('Player').count().reset_index()

        list_foul = []
        for player_id in self.dict_player_fullname().keys():
            no_fouls = 0
            f = (df.Player == player_id)
            if (f.sum() == 1):
                no_fouls = (list(df.loc[f]['FoulType'])[0])
                
            foul = [player_id, no_fouls]
            list_foul.append(foul)

        foul_df = pd.DataFrame.from_records(list_foul, columns=['Player', 'Foul'])

        return foul_df
    
    
    def __non_shooting_stat(self):
        """
        """
        df = self.events
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
        non_shot_df['MatchId'] = self.match_id
        
        all_non_shot_stat_df = pd.DataFrame.merge(non_shot_df, self.__assist_stat()) # join to get assists data
        all_non_shot_stat_df2 = pd.DataFrame.merge(all_non_shot_stat_df, self.__foul_stat()) # join to get fouls data

        return all_non_shot_stat_df2
        
        
        
######
## Getters
######    
    def get_roster(self):
        return self.__roster()

    def get_shooting_stat(self):
        return self.__shooting_stat()

######
## List of values
######
    
    def LOV_fouls(self):
        LOV_fouls = pd.DataFrame(self.events.FoulType.astype('str').unique(), columns=['FoulType'])
        LOV_fouls['FoulTypeDesc'] = LOV_fouls.replace(self.__dic.foul_description)
        return LOV_fouls
        
    def LOV_shots(self):
        LOV_shots = pd.DataFrame(self.events.ShotResult.unique(), columns=['ShotResult'])
        LOV_shots['ShotResultDesc'] = LOV_shots.replace(self.__dic.shot_description)
        return LOV_shots
    
    def dict_team_names(self):
        return {"Home": self.home_team, "Away": self.away_team}
    
    def dict_player_fullname(self):    
        player_full_df = self.roster
        player_fullname_df = pd.DataFrame(player_full_df.FirstName + ' ' + player_full_df.LastName, columns=['FullName'])
        player_fullname_df.index = player_full_df.Id
        dict_player_fullname = player_fullname_df.to_dict()['FullName']
        return dict_player_fullname
    
    def dict_player_team(self):
        player_full_df = self.roster
        player_team_df = player_full_df['Team']
        player_team_df.index = player_full_df.Id
        player_team_df.column = ['Team']
        dict_player_team = player_team_df.to_dict()
        return dict_player_team
    
    def dict_is_playerid_starter(self):
        dict_player_starter = self.players_all_playtimes[['Player', 'In']] \
                        .groupby(['Player']) \
                        .min()['In'] \
                        .apply(lambda x: 'Y' if x == pd.to_datetime('1900-01-01 00:00:00') else 'N') \
                        .to_dict()

        return dict_player_starter
    
    
######
## Save to S3
######
    
    def save_dataframe_s3(self, df, folder):
        competition = 'blno/' + folder + '/'
        s3_resource = boto3.resource('s3')
        bucket_name = 'hubie'
        json_data = df.to_json(force_ascii=False, date_format='iso', orient='records', lines=True)
        

        s3object = s3_resource.Object(bucket_name, competition + self.match_id + '.json')

        s3object.put(
            Body=(bytes(json_data.encode('UTF-8')))
        )
        
######
### Summary file
######
    '''list_event_type = events['MatchEventType'].unique()
for event in list_event_type:
    print(events.loc[events['MatchEventType'] == event]
          .groupby(['MatchEventType', 'HomeAway'])['MatchEventType']
          .count()
          .sort_index(ascending=False))
    print("-------------------------------------")'''