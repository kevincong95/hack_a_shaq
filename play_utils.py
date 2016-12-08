import requests  
import json
import csv  
import pandas as pd
import nbawebstats as nbaws
import pdb
from datetime import datetime as dt

'''
Whether or not the datatuple is describing a made free throw for the given team.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has made a free throw. 
'''
def ft_made(play, team):
    return play[3] == 3 and play[19] == team and play[11] != ''

'''
Whether or not the datatuple is describing a missed free throw for the given team.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has missed a free throw. 
'''
def ft_missed(play, team):
    return play[3] == 3 and play[19] == team and play[11] == ''

'''
Whether or not the datatuple is describing a free throw attempt for the given team.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has attempted a free throw. 
'''
def ft_att(play, team):
    return ft_made(play, team) or ft_missed(play, team)

'''
Whether or not the datatuple is describing a made field goal for the given team.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has made a field goal. 
'''
def fg_made(play, team):
    return play[3] == 1 and play[19] == team

'''
Whether or not the datatuple is describing a missed field goal for the given team.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has missed a field goal. 
'''
def fg_missed(play, team):
    return play[3] == 2 and play[19] == team

'''
Whether or not the datatuple is describing a field goal attempt for the given team.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has attempted a field goal. 
'''
def fg_att(play, team):
    return play[3] in [1,2] and play[19] == team

'''
The number of points the given team scored on the play, which should be a FG or FT attempt.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: 1 if play is made free throw, 2 if made 2-pointer, 3 if made 3-pointer, 0 otherwise.
'''
def points(play, team):
    if ft_made(play, team):
        return 1
    elif not fg_made(play, team):
        return 0
    elif (play[8] + play[10]).find("3PT") > -1:
        return 3
    return 2

'''
Whether or not the datatuple is describing a turnover for the given team.
@param play: Description of play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has committed a turnover. 
'''
def turnover(play, team):
    return play[3] == 5 and play[19] == team 

'''
Whether or not the datatuple is describing an offensive rebound for the given team.
@param prev: Description of play immediately before target play.
@param play: Description of target play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has grabbed an offensive rebound (off its own missed FG / FT attempt).
'''
def oreb(prev, play, team):
    return play[3] == 4 and play[19] == team and (fg_missed(prev, team) or (ft_missed(prev, team) and play[13] >= 4))


'''
Whether or not the datatuple is describing a defensive rebound for the given team.
@param prev: Description of play immediately before target play.
@param play: Description of target play in pd.DataFrame form.
@param team: A 3-letter string indicating the team.
@return: True if the team has grabbed a defensive rebound (off opponent's missed FG / FT attempt).
'''
def dreb(prev, play, team):
    return play[3] == 4 and play[19] == team and prev[19] != team

'''
Whether or not the datatuple is describing a completed possession for the given team.
@param prev: Description of play immediately before target play.
@param play: Description of target play in pd.DataFrame form.
@param nxt: Description of play immediately after target play.
@param team: A 3-letter string indicating the team.
@return: True if the team has completed a possession (made FG or turnover or opponent DREB off missed FG).
'''
def poss(prev, play, nxt, team, opp):
    if ft_att(play, team):
        lane = nxt
        if ft_made(play, team):
            return nxt[19] == opp or (nxt[19] == team and nxt[3] == 6) 
    return fg_made(play, team) or dreb(prev, play, opp) or turnover(play, team)

'''
Whether or not the datatuple is describing the player being substituted out of the game.
@param play: Description of target play in pd.DataFrame form.
@param playerid: An up to 7-digit number corresponding to a playerid on nba.com.
@return: True if the selected player is being removed from the game on this play.
'''
def subbed_out(play, playerid):
    return play[3] == 8 and play[14] == playerid

'''
Whether or not the datatuple is describing the player being substituted into the game.
@param play: Description of target play in pd.DataFrame form.
@param playerid: An up to 7-digit number corresponding to a playerid on nba.com.
@return: True if the selected player is being put into the game on this play.
'''
def subbed_in(play, playerid):
    return play[3] == 8 and play[21] == playerid

'''
The amount of time the given player rests after being substituted out of the game.
@param pbp: Play-by-play log.
@param index: Index of first play in pbp.
@param playerid: An up to 7-digit number corresponding to a playerid on nba.com.
@return: The amount of time the player rests after being removed from the game,
as well as what the score margin is when he re-enters. -1 if the first play does not
correspond to player being substituted out.
'''
def rest_time_margin(pbp, index, playerid, loc):
    sub_out = [play for play in pbp if play[0] == index][0]
    if not sub_out or not subbed_out(sub_out, playerid):
        return -1
    start_time = clock_to_secs(sub_out[7])
    margin = -1
    entire_quarter = False
    while not subbed_in(sub_out, playerid) and index <= pbp[-1][0] and not entire_quarter:
        sub_out = [play for play in pbp if play[0] == index][0]
        if sub_out[3] == 13:
            entire_quarter = True
            if sub_out[12] != "":
                margin = sub_out[12]
                if margin == 'TIE':
                    margin = 0
        index += 1
    return (start_time - clock_to_secs(sub_out[7]), int(margin) * loc)

'''
Get a player's free throw rate for a given season (13-14, 14-15, or 15-16 only).
@param playerid: An up to 7-digit number corresponding to a playerid on nba.com.
@param season: If season = n, we check stats from the [2000 + n] - [2001 + n] season.
@return: The player's free throw rate for that season.
The commented out code calls the stats.nba.com API through the package nbawebstats.
'''
def ft_rate(playerid, season):
    # career_stats = nbaws.request_stats('player-career-stats', {'PlayerID': playerid})
    # by_season = dict(career_stats)['season-totals-regular']
    # for year in by_season:
    #     if int(year['SEASON_ID'][2:4]) == season:
    #         return year['FT_PCT']
    players = pd.DataFrame.from_csv('all_players.csv')
    player_stats = players[players.PERSON_ID == playerid]
    col = "FT_RATE" + str(season)
    return player_stats[col].iloc[0]

'''
Given the time showing on the clock, convert it into seconds.
@param clock: Amount of time left on the clock, in the format [mins]:[secs].
@return: The number of seconds left.
'''
def clock_to_secs(clock):
    mins = int(clock.split(":")[0])
    secs = int(clock.split(":")[1])
    return 60 * mins + secs

'''
Given the number of seconds left in a quarter, convert it into a game clock reading.
@param secs: The number of seconds left in the quarter.
@return: Amount of time left on the clock, in the format [mins]:[secs].
'''
def secs_to_clock(secs):
    mins = secs // 60
    secs = secs % 60
    return str(mins).rjust(2, '0') + ":" + str(secs).rjust(2, '0')

'''
A team's coach (last, first) on a given date.
@param date: The date on which we are targeting, as a Python datetime object.
@param team: @param team: A 3-letter string indicating the team.
@return: The team's coach on that date in the format (last_name, first_name).
'''
def get_coach(date, team):
    coaches = pd.DataFrame.from_csv('coaches.csv')
    coach_history = coaches[coaches.city == team]
    stint = coach_history[(pd.to_datetime(coach_history.startDate) <= date) &
                          (pd.to_datetime(coach_history.endDate) > date)]
    return stint['coachLast'].iloc[0], stint['coachFirst'].iloc[0]

'''
Get the date (pd) on which the game corresponding to a gameID was played.
@param gameID: A 10-digit number representing the game's ID number according to nba.com.
@param season: If season = n, we check stats from the [2000 + n] - [2001 + n] season.
@param playoffs: If true, the game is a playoff game. By default, the game is a regular season game.
@return: A Python datetime object, representing the date on which the game was played.
'''
def get_date(gameID, season, playoffs = False):
    seasontype = 'playoff' if playoffs else 'reg'
    schedule = pd.DataFrame.from_csv('games{0}{1}{2}.csv'.format(str(season), str(season+1), seasontype))
    game = schedule[schedule.GAME_ID == gameID]
    return pd.to_datetime(game.GAME_DATE.unique()[0])
