Master table:
eventId - Unique reference to hacking instance, INTEGER, UNIQUE, PRIMARY KEY

gameId - Game in which event occurred, INTEGER

season - Season in which event occurred, INTEGER #n represents [2000+n] - [2001+n] season

date - Date on which event occurred

playoffs - 0 if event occurred in regular season, 0 if in playoffs

teamName - City in which hacking team is located, VARCHAR(3) #ATL, BOS,...UTA, WSH

oppName - City in which opponent is located, VARCHAR(3) #ATL, BOS,...UTA, WSH

teamCoachId - Reference to coach calling for hacking, INTEGER

location - 1 if hacking team is home, -1 if away, INTEGER

hackedPlayerId - Reference to player being hacked, INTEGER, FOREIGN KEY

hackedFTRate - Hacked player's FT rate for the season, FLOAT

numPoss - Number of possessions achieved while hacking, INTEGER

FTM - Opponent's number of free throws made during hacking, INTEGER

FTA - Opponent's number of free throws attempted during hacking, INTEGER

playerRemoved - 1 if hacked player removed from the game after shooting FTs on his team's last possession, 0 otherwise INTEGER

playerRestTime - For many seconds was the hacked player removed from the game? DOUBLE

returnMargin - Margin when hacked player re-entered game, INTEGER

startQ - Quarter in which hacking begins, INTEGER #5 for 1OT, 6 for 2OT, and so on 

startTime - # of seconds remaining in period, DOUBLE #defined as when the first FTs are shot

startMargin - Margin when hacking begins, INTEGER #positive means hacking team is leading

endQ - Quarter in which hacking ends, INTEGER #5 for 1OT, 6 for 2OT, and so on 

endTime - # of seconds remaining in period, DOUBLE #hacked player removed from game, or a possession completed without hacking

endMargin - Margin when hacking ends, INTEGER #positive means hacking team is leading

2ndChancePts - Number of points scored by opponent off offensive rebounds of missed FTs, INTEGER

addlFT - Number of non-shooting foul free throw attempts for opponent after hacking (hacking triggers early bonus), INTEGER

win - 1 if hacking team won the game, 0 otherwise, INTEGER

inbound - 1 if foul occurred on an inbound play, 0 otherwise, INTEGER #potentially based on an isolated but nevertheless egregious incident

Team table:

teamId - Need a new one for each team+coach combo, INTEGER, UNIQUE, PRIMARY KEY, AUTO INCREMENT

city - City in which team is located, VARCHAR(3) #ATL, BOS,...UTA, WSH

nickname - Hawks, Celtics,...Jazz, Wizards, VARCHAR

season - Season in which team played, INTEGER #n represents [2000+n] - [2001+n] season

coachFirst - Coach's first name, VARCHAR

coachLast - Coach's last name, VARCHAR

GPReg - Number of regular season games team played under coach, INTEGER

GPPoff - Number of playoff games team played under coach, INTEGER
