import queue
import time
from threading import Thread

from bs4 import BeautifulSoup
import re
import urllib.request
import sys

DEBUG = False
DEBUG_POST_GAMES = True
INTERVAL = 15
# debug returns: None, 5/12, 6/12, 6/12, 7/12, None, None, 5/12 + 5/12, 5/12 + 6/12, 5/12 + 6/12, 6/12, None
debugsites = ["websitewithout.html", "websitewith5-12.html", "websitewith6-12.html", "websitewith6-12.html", "websitewith7-12.html", "websitewithout.html", "websitewithout.html", "websitewithdouble5-12.html", "websitewithdouble6-12.html", "websitewithdouble6-12.html", "websitewith6-12.html", "websitewithout.html", "websitewith5-12-ent.html", "websitewithout.html"]
#debugsites = ["websitewithout.html", "websitewith5-12.html", "websitewith6-12.html", "websitewith6-12.html", "websitewith7-12.html", "websitewithout.html", "websitewithout.html"]
#debugsites = ["websitewithout.html", "websitewith5-12.html", "websitewithout.html", "websitewithout.html"]


NEWGAME = "NEW"
SAMEGAME = "SAME"
DISAPPEAREDGAME = "DISAPPEARED"


class OpenGame():
    def __repr__(self):
        return self.status + ": " + "OpenGame{" + self.botname + " in " + self.country + ": " + self.gamename + "(" + self.players + ")}"

    def __init__(self, botname, country, gamename, players):
        self.botname = botname
        self.country = country
        self.gamename = gamename
        self.players = players
        self.status = NEWGAME
        self.msgstr = None
        self.msgobj = None
        self.previous = None

    def is_on_same_bot(self, game2):
        if not game2:  # can't call this on None, so no problem
            return False
        assert isinstance(game2, OpenGame)
        return self.botname == game2.botname

    def equals_name(self, game2):
        if not game2:  # can't call this on None, so no problem
            return False
        assert isinstance(game2, OpenGame)
        return self.gamename == game2.gamename

    def equals_exactly(self, game2):
        assert isinstance(game2, OpenGame)
        return self.gamename == game2.gamename and self.players == game2.players

    def add_prev_game(self, last_open_game):
        self.previous.append(last_open_game)


class BackgroundRequester(Thread):
    def __init__(self, cb):
        super().__init__()
        self.cb = cb

    def run(self):
        while True:
            self.cb()
            time.sleep(INTERVAL)


class Requester():
    requestscount = 0

    def __init__(self, DEBUG_ARG):
        if DEBUG_ARG:
            global DEBUG
            DEBUG = DEBUG_ARG
            print("Debugging enabled")
        self.mmhCurrentGames = {}
        self.backgroundtask = BackgroundRequester(self.query_evotag_games)
        self.backgroundtask.start()
        self.newGamesQueue = []  # not thread safe but we don't care

    def get_makemehost_as_str(self):
        if DEBUG:
            if not DEBUG_POST_GAMES:
                return ""
            num = self.requestscount % (len(debugsites) - 1)
            with open(debugsites[num], "r") as f:
                # print("Debug: opening " + str(num) + ": " + f.name, self.requestscount)
                html_doc = f.read()
        else:
            URL = "http://makemehost.com/games.php"
            try:
                html_doc = urllib.request.urlopen(URL).read().decode("utf8", errors="replace")
            except urllib.error.URLError as e:
                print("urlopen error", e)
                return ""
            except Exception as e:
                print("urlopen exception", e)
                return ""
        self.requestscount += 1
        return html_doc

    def fill_in_strings(self, currentgames, disappearedgames):
        for currentgame_botname in currentgames:
            currentgame = currentgames[currentgame_botname]
            #print("str for", currentgame)
            currentgame.msgstr = "[OPEN] Game hosted on " + currentgame.botname + " [" + currentgame.country + "]: `" + currentgame.gamename + "`\t(" + currentgame.players + ")"
        for disappearedgame in disappearedgames:
            disappearedgame.msgstr = "Game started (or cancelled): `" + disappearedgame.gamename + "` with " + disappearedgame.players + "!"

    def process_changes(self, new_open_games):
        # print("Process changes for: ", "last games", self.mmhCurrentGames, "new games", new_open_games)
        current_open_games = {}
        disappeared_games = []

        for new_botname in new_open_games.keys():
            newgame: OpenGame = new_open_games[new_botname]
            oldgame: OpenGame = self.mmhCurrentGames[new_botname] if new_botname in self.mmhCurrentGames else None
            if new_botname in self.mmhCurrentGames.keys() and newgame.is_on_same_bot(oldgame):
                # we have already seen this game last update
                newgame.previous = oldgame
                newgame.status = SAMEGAME
                newgame.msgobj = oldgame.msgobj
                current_open_games[new_botname] = newgame
                # print("Same: ", oldgame, newgame)
            else:
                # this is a new game
                current_open_games[new_botname] = new_open_games[new_botname]
                current_open_games[new_botname].status = NEWGAME
                # print("New: ", newgame)
        for last_botname in self.mmhCurrentGames.keys():
            if last_botname not in new_open_games.keys():
                # this game was open last time but is not open now
                self.mmhCurrentGames[last_botname].status = DISAPPEAREDGAME
                disappeared_games.append(self.mmhCurrentGames[last_botname])

        self.mmhCurrentGames = current_open_games
        self.fill_in_strings(current_open_games, disappeared_games)
        return current_open_games, disappeared_games

    def parse_html(self, html_doc):
        if html_doc == "":
            return None
        # work around VERY broken html before the ent games
        for _ in range(50):  # TODO: Fix this until there aren't </tr></tr> left
            html_doc = html_doc.replace("</tr></tr>", "</tr>")
        html_doc = html_doc.replace(" </tr><tr><td>Ent", "<tr><td>Ent")
        #print(html_doc)
        soup = BeautifulSoup(html_doc, 'html.parser')
        divs = soup.find('div', {"class": "refreshMeMMH"})
        if not divs:
            print("Error: Table not found!")
            return None
        rows = divs.table.find_all('tr')

        table_games = {}
        for row in rows:
            data = row.find_all("td")
            botname = data[0].get_text()
            country = data[1].get_text()
            gn = data[3].get_text()
            players = data[4].get_text()
            #print(gn)
            m = re.search('.*evo.*tag.*', gn.lower())
            #print(m)
            if m:
                game = OpenGame(botname, country, gn, players)
                table_games[botname] = game

        divsent = soup.find('div', {"class": "refreshMeENT"})
        rowsent = divsent.table.find_all('tr')
        # print("searching ent", divsent)
        for row in rowsent:
            data = row.find_all("td")
            botname = data[0].get_text()
            country = "-"
            gn = data[1].get_text()
            players = data[2].get_text()
            # print(gn)
            m = re.search('.*evo.*tag.*', gn.lower())
            # print(m)
            # print("ent...", gn)
            if m:
                game = OpenGame(botname, country, gn, players)
                table_games[botname] = game

        for g in table_games:
            #print("found " + str(g))
            pass
        return table_games

    def query_evotag_games(self):
        table_games = self.parse_html(self.get_makemehost_as_str())
        if table_games is None:
            return
        self.newGamesQueue.append(table_games)
        # print("Queried new", table_games)

    def has_game_updates(self):
        return len(self.newGamesQueue) > 0

    def get_evotag_games(self):
        processed_games = self.process_changes(self.newGamesQueue.pop(0))
        if processed_games:
            return processed_games
        else:
            print("Process_changes failed, this doesn't happen")
            return None, None

EDITMODE = "EDIT"
PRINTMODE = "PRINT"

if __name__ == "__main__":
    debugarg = False
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        debugarg = True
    r = Requester(debugarg)
    rnum = len(debugsites) if DEBUG else 5
    for i in range(rnum):
        prefix = "Request " + str(i)
        currentgames, disappearedgames = r.get_evotag_games()

        for num, botname in enumerate(currentgames.keys()):
            currentgame = currentgames[botname]
            #print(botname, currentgame)
            if currentgame.msgstr:
                print(prefix, "[" + currentgame.status + "]", currentgame.msgstr)
        for disappearedgame in disappearedgames:
            print(prefix, "[" + disappearedgame.status + "]", disappearedgame.msgstr)

        if not DEBUG:
            time.sleep(2)