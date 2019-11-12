from logic.analysis import Analysis
from logic.utility import Utility
import pandas as pd
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)

#match_id = 7032956
#match_id = 7032913
#match_id = 7032979
#match_id = 7032949

all_matches = [7032956, 7032913, 7032979, 7032949]
'''u = Utility(events_file=str(match_id) + "_MatchEventsViewModel.json")
shoot_stat = u.get_shooting_stat()
print(shoot_stat)'''


for match_id in all_matches:
    print(match_id)
    a = Analysis(match_id=match_id, competition='BLNO Kvinner Grunnserie', dry_run=False)
    a.run_all_analyses()
#df = a.match_header()
#df = a.player_statistic()
#df['MinuteRound'] = df.Minute.astype(str).str[-5:-3]
#a.point_accumulation() #[['MinuteRound', 'Difference']]#.reset_index(drop=True)
#df['DifferenceHome'] = df.Difference.apply(lambda x: x if x >= 0 else 0)
#df['DifferenceAway'] = df.Difference.apply(lambda x: x if x < 0 else 0)
#df['MinuteRound'] = df.Minute.astype(str).str[-5:-3]
#df = a.assist()
#print(df)
