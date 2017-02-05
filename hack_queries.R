hacks <- read.csv("hack_master.csv")
hackedPlayers <- table(hacks$HackedPlayerID)
hackedIDs <- names(hackedPlayers) #IDs of players targeted
hackers <- table(hacks$Team) #who likes to hack?
hackees <- table(hacks$Opp) #which teams get hacked?
allPlayers <- read.csv("all_players.csv")
targets <- hackedPlayers[which(hackedPlayers >= 10)] #players hacked more than 10 times
allPlayers <- allPlayers[allPlayers$ROSTERSTATUS == 1,]
allPlayers <- allPlayers[order(allPlayers$FT_RATE15),]
vulnerable <- allPlayers[allPlayers$FT_RATE15 > 0,]
vulnerable <- vulnerable[vulnerable$FT_RATE15 < 0.7,]
#new for Spring 2017
bestTargets <- as.numeric(names(targets))
majorHacks <- hacks[is.element(hacks$HackedPlayerID, bestTargets), ] #only consider hacking of most popular targets from here on out
hackers <- table(majorHacks$Team)
hackees <- table(majorHacks$Opp)
frequentHackers <- hackers[which(hackers >= 20)]
criticalGames <- majorHacks[is.element(majorHacks$Team, names(frequentHackers)), ]
affectedGames <- unique(criticalGames$GameID)
