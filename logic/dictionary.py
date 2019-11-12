class Dictionary():
    def __init__(self):
        pass

    period_name_list = {1: '1. period',
                        2: '2. period',
                        3: '3. period',
                        4: '4. period'}
    
    foul_description = {'200448.0': "Side Ball",
                        '200461.0': "Free Throw",
                        '200449.0': "Offensive Foul",
                        '200450.0': "Unsportsmanlike Foul"}
    
    shot_description = {200445: "Missed 1P",
                        200444: "Made 1P",
                        200581: "Missed 2P",
                        200443: "Made 2P",
                        200580: "Missed 3P",
                        200442: "Made 3P"}
    
    shot_result_points = {200445: 0,
                          200444: 1,
                          200581: 0,
                          200443: 2,
                          200580: 0,
                          200442: 3}