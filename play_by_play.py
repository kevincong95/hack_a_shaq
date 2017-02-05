import requests  
import json
import csv
import os.path
import pandas as pd
import nbawebstats as nbaws
from time import sleep
from collections import OrderedDict
import play_utils as utils
import pdb

#list of headers for play-by-play data
params = {1:'GAME_ID', 2:'EVENTNUM', 3:'EVENTMSGTYPE', 4:'EVENTMSGACTIONTYPE', 5:'PERIOD', 6:'WCTIMESTRING', 
7:'PCTIMESTRING', 8:'HOMEDESCRIPTION', 9:'NEUTRALDESCRIPTION', 10:'VISITORDESCRIPTION', 11:'SCORE', 12:'SCOREMARGIN',
13:'PERSON1TYPE', 14:'PLAYER1_ID', 15:'PLAYER1_NAME', 16:'PLAYER1_TEAM_ID', 17:'PLAYER1_TEAM_CITY',
18:'PLAYER1_TEAM_NICKNAME', 19:'PLAYER1_TEAM_ABBREVIATION', 20:'PERSON2TYPE', 21:'PLAYER2_ID', 22:'PLAYER2_NAME',
23:'PLAYER2_TEAM_ID', 24:'PLAYER2_TEAM_CITY', 25:'PLAYER2_TEAM_NICKNAME', 26:'PLAYER2_TEAM_ABBREVIATION', 
27:'PERSON3TYPE', 28:'PLAYER3_ID', 29:'PLAYER3_NAME', 30:'PLAYER3_TEAM_ID', 31:'PLAYER3_TEAM_CITY', 32:'PLAYER3_TEAM_NICKNAME',
33:'PLAYER3_TEAM_ABBREVIATION'}
hack_keys = ['GameID', 'Season', 'Date', 'Playoffs', 'Team', 'Opp', 'Coach', 'Location', 'HackedPlayerID', 'HackedFTRate',
            'StartQ', 'StartTime', 'StartMargin', 'PlayerRemoved', 'PlayerRestTime', 'EndQ', 'EndTime', 'EndMargin',
            'NumPoss', 'FTM', 'FTA', 'ReturnMargin', '2ndChancePts', 'Win']
#Yes NBA.com, I am a user agent
userHeaders = {
    'User-Agent': 'MMozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36',
    'From': 'dr.boar@gmail.com'
}

'''
Saves a game's play-by-play log in dataframe format.
@param season: n corresponds to the (2000+n)-(2001+n) NBA season.
@param num: See below for game number format used by NBA.com.
@param playoffs: Whether or not we are looking for a playoff game.
'''
def playByPlay(season, num, playoffs = False):
    game = gameID(season, num, playoffs)
    season = "20{0}-{1}".format(season, season+1)
    seasonType = "Playoffs" if playoffs else "Regular+Season"
    url = "http://stats.nba.com/stats/playbyplayv2?EndPeriod=10&EndRange=55800&GameID={0}&RangeType=2&Season={1}&SeasonType={2}&StartPeriod=1&StartRange=0".format(game, season, seasonType)
    response = requests.get(url, headers=userHeaders)
    if response.status_code != 200:
        print(url)
        print(response.status_code)
        f = open('bad_urls.txt', 'a')
        f.write(url + "\n")
        f.close()
        return
    data = json.loads(response.text)
    headers = data['resultSets'][0]['headers']
    plays = data['resultSets'][0]['rowSet']
    df = pd.DataFrame(plays,columns=headers) 
    df.to_csv(game + ".csv")

'''
Return an NBA.com game ID.
@param num: Regular season: 1 <= num <= 1230
Playoffs: A 3-digit number XYZ.
X corresponds to the round number; 1 for conference quarterfinals, 4 for NBA finals.
Y corresponds to the series number.
Z corresponds to the game number; 1 <= Z <= 7.
@param playoffs: 
'''
def gameID(season, num, playoffs):
    if playoffs:
        return "004" + str(season) + str(num).rjust(5, '0') if validPlayoffID(num) else None
    else:
        return "002" + str(season) + str(num).rjust(5, '0')

'''
Checks that the 3-digit number can represent an NBA playoff game.
'''
def validPlayoffID(num):
    gameNum = num % 10
    if gameNum < 1 or gameNum > 7:
        return False
    seriesNum = (num // 10) % 10 
    if num // 100 == 1:
        return seriesNum <= 7
    elif num // 100 == 2:
        return seriesNum <= 3
    elif num // 100 == 3:
        return seriesNum <= 1
    elif num // 100 == 4:
        return seriesNum == 0
    else:
        return False

#pbp may NOT start with a foul that sends a hacking target to the line!!!
def parse_pbp(pbp, season, num, playoffs = False):
    hacking = False
    margin = 0
    index = pbp.iloc[0].name
    numPoss = 0
    FTM = 0
    FTA = 0
    sec_chance = False
    sec_chance_pts = 0
    prev = ()
    all_hacks = []
    pbp = list(pbp.itertuples())
    for play in pbp:
        #pdb.set_trace()
        desc = play[8] if not play[10] else play[10]
        if play[12]:
            margin = play[12] #this variable is from home team's POV
            if margin == 'TIE':
                margin = 0
        if (desc.lower().find('take')
            > -1) and (desc.lower().find('pn') > -1) and not (play[5]
                                                              == 4 and utils.clock_to_secs(play[7])
                                                              < 45) and not hacking:
            hacked_id = play[21]
            ftr = utils.ft_rate(hacked_id, season)
            if ftr < 0.7: #hack-a-(whoever) in progress
                hacking = True
                event = OrderedDict()
                event['GameID'] = int(gameID(season, num, playoffs))
                event['Season'] = season
                event['Date'] = utils.get_date(event['GameID'], season, playoffs)
                event['Playoffs'] = 1 if playoffs else 0
                event['Team'] = play[19]
                event['Opp'] = play[26]
                event['Coach'] = utils.get_coach(event['Date'], event['Team'])
                if desc == play[8]:
                    event['Location'] = 1
                else:
                    event['Location'] = -1
                event['HackedPlayerID'] = hacked_id
                event['HackedFTRate'] = ftr
                event['StartQ'] = play[5]
                event['StartTime'] = play[7]
                event['StartMargin'] = int(margin) * event['Location']
                #event['JumpOnBack'] = 1 if (prev[3] == 3 or pbp.ix[index - 2][2] == 3)else 0 #This usually occurs on FT attempts
        if hacking:
            #update parameters for made FTs
            if utils.ft_made(play, event['Opp']):
                FTA += 1
                FTM += 1
                if sec_chance:
                    sec_chance_pts += 1
            #and missed ones
            elif utils.ft_missed(play, event['Opp']):
                FTA += 1
            #hacking team gets an extra possession
            elif index < len(pbp) - 1 and utils.poss(prev, play, pbp[index + 1], event['Team'], event['Opp']):
                numPoss += 1
            #hacked team can get 2nd chance points off missed FT
            elif utils.oreb(prev, play, event['Opp']):
                sec_chance = True
            #how to tally 2nd chance points
            if sec_chance and utils.points(play, event['Opp']):
                sec_chance_pts += utils.points(play, event['Opp'])
            if sec_chance and index < len(pbp) - 1 and utils.poss(prev, play, pbp[index + 1], event['Opp'], event['Team']):
                sec_chance = False
            #To stop hacking, remove the hacked player.
            elif utils.subbed_out(play, hacked_id):
                hacking = False
                event['PlayerRemoved'] = 1
                removal_info = utils.rest_time_margin(pbp, index, hacked_id, event['Location'])
                event['PlayerRestTime'] = removal_info[0]
            #The hacked team must attempt a FG (without FT OREB), or have someone else get fouled.
            elif (utils.fg_att(play, event['Opp']) and not sec_chance) or (play[3] == 6 and play[19] == event['Team'] and play[21] != hacked_id):
                hacking = False
                event['PlayerRemoved'] = 0
                event['PlayerRestTime'] = 0
            if not hacking:
                event['EndQ'] = play[5]
                event['EndTime'] = play[7]
                event['EndMargin'] = int(margin) * event['Location']
                event['NumPoss'] = numPoss
                event['FTM'] = FTM
                event['FTA'] = FTA
                event['ReturnMargin'] = removal_info[1] if event['PlayerRemoved'] else float('inf')
                event['2ndChancePts'] = sec_chance_pts
                all_hacks.append(event)
                numPoss = 0
                FTM = 0
                FTA = 0
                sec_chance_pts = 0
        prev = play
        index += 1
    for event in all_hacks:
        if int(margin) * event['Location'] > 0:
            event['Win'] = 1
        else:
            event['Win'] = 0
    return all_hacks

def find_hacks(season, num, playoffs = False):
    if playoffs:
        path = '20{0}-{1}playoffs/004{2}{3}.csv'.format(str(season), str(season + 1), str(season), str(num).rjust(5, '0'))
    else:
        path = '20{0}-{1}reg/002{2}{3}.csv'.format(str(season), str(season + 1), str(season), str(num).rjust(5, '0'))
    pbp = pd.DataFrame.from_csv(path)
    pbp = pbp.fillna(value = "")
    return parse_pbp(pbp, season, num, playoffs)

def collect_hacks(season, playoffs = False):
    master = open('hack_master.csv', 'a')
    fp = csv.DictWriter(master, hack_keys)
    pathf = '20{0}-{1}playoffs/004{2}00{3}.csv'
    if not playoffs:
        for i in range(1, 1231):
            hacks = find_hacks(season, i)
            if hacks:
                fp.writerows(hacks)
    else:
        for i in range(100, 407):
            if os.path.exists(pathf.format(str(season), str(season + 1),
                                           str(season), str(i))):
                hacks = find_hacks(season, i, True)
                if hacks:
                    fp.writerows(hacks)
    master.close() #ALWAYS close a file after you're done writing to it!!!

def penalty_time(gameID, team, quarter):
	if gameID[0] == '4':
		path = '20{0}-{1}playoffs/00{2}.csv'.format(str(season), str(season + 1), gameID)
	elif gameID[0] == '2':
		path = '20{0}-{1}reg/00{2}.csv'.format(str(season), str(season + 1), gameID)
	pbp = pd.DataFrame.from_csv(path)
    pbp = pbp.fillna(value = "")
    pbp = list(pbp.itertuples())
    index = 0
    play = pbp[index]
    while play[5] != quarter:
    	index += 1
    	play = pbp[index]
    tmFouls = 0
    limit = 5 if quarter <= 4 else 4
    while tmFouls < limit:
    	if utils.team_foul(play, team):
    		tmFouls += 1
    	elif tmFouls < limit - 2 and utils.clock_to_secs(play[7]) <= 120:
    		tmFouls = limit - 2
    	elif play[3] == 13:
    		return 0
    	index += 1
    return utils.clock_to_secs(play[7])


'''
THOMPSON'S SHOT CHART
http://stats.nba.com/stats/playerdashptshots?DateFrom=&DateTo=&
GameSegment=&LastNGames=0&LeagueID=00&Location=&Month=0&OpponentTeamID=0&
Outcome=&PerMode=PerGame&Period=0&PlayerID=202691&Season=2015-16&
SeasonSegment=&SeasonType=Regular+Season&TeamID=0&VsConference=&VsDivision=
'''

'''
CURRY'S SHOT LOG
http://stats.nba.com/stats/shotchartdetail?CFID=33&CFPARAMS=2015-16&
ContextFilter=&ContextMeasure=FGA&DateFrom=&DateTo=&GameID=&GameSegment=&
LastNGames=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&
Outcome=&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerID=201939&PlusMinus=N&
Position=&Rank=N&RookieYear=&Season=2015-16&SeasonSegment=&SeasonType=Regular+Season&
TeamID=0&VsConference=&VsDivision=&mode=Advanced&showDetails=0&showShots=1&showZones=0
'''

'''
PLAY-BY-PLAY DATA HERE:
http://stats.nba.com/stats/playbyplayv2?EndPeriod=10&EndRange=55800&
GameID=0021501230&RangeType=2&Season=2015-16&SeasonType=Regular+Season&StartPeriod=1&StartRange=0
PARAMS: GameID, Season, SeasonType
'''
