import time
from bs4 import BeautifulSoup
import re
import urllib.request

DEBUG = False
# debug returns: None, 5/12, 6/12, 6/12, 7/12, None, None, 5/12 + 5/12, 5/12 + 6/12, 5/12 + 6/12, 6/12, None
debugsites = ["websitewithout.html", "websitewith5-12.html", "websitewith6-12.html", "websitewith6-12.html", "websitewith7-12.html", "websitewithout.html", "websitewithout.html", "websitewithdouble5-12.html", "websitewithdouble6-12.html", "websitewithdouble6-12.html", "websitewith6-12.html", "websitewithout.html", "websitewith5-12-ent.html", "websitewithout.html"]
#debugsites = ["websitewithout.html", "websitewith5-12.html", "websitewith6-12.html", "websitewith6-12.html", "websitewith7-12.html", "websitewithout.html", "websitewithout.html"]

NEWGAME = "NEW"
SAMEGAME = "SAME"
DISAPPEAREDGAME = "DISAPPEARED"

class OpenGame():
    botname = None
    country = None
    status = None
    gamename = None
    players = None
    previous = None
    userptr = None
    msgstr = None

    def __repr__(self):
        return self.status + ": " + "OpenGame{" + self.botname + " in " + self.country + ": " + self.gamename + "(" + self.players + ")}"

    def __init__(self, botname, country, gamename, players):
        self.botname = botname
        self.country = country
        self.gamename = gamename
        self.players = players
        self.status = NEWGAME

    def same_game(self, game2):
        assert isinstance(game2, OpenGame)
        return self.botname == game2.botname

    def equals_name(self, game2):
        assert isinstance(game2, OpenGame)
        return self.gamename == game2.gamename

    def equals_exactly(self, game2):
        assert isinstance(game2, OpenGame)
        return self.gamename == game2.gamename and self.players == game2.players

    def add_prev_game(self, last_open_game):
        self.previous.append(last_open_game)

    def update_values_from(self, oldgame):
        self.userptr = oldgame.userptr


class Requester():
    last_open_games = {}
    requestscount = 0

    def __init__(self):
        pass

    def get_makemehost_as_str(self):
        if DEBUG:
            num = self.requestscount % (len(debugsites) - 1)
            with open(debugsites[num], "r") as f:
                # print("Debug: opening " + str(num) + ": " + f.name)
                html_doc = f.read()
        else:
            URL = "http://makemehost.com/games.php"
            html_doc = urllib.request.urlopen(URL).read().decode("utf8")
        self.requestscount += 1
        return html_doc

    def fill_in_strings(self, currentgames, disappearedgames):
        for currentgame_botname in currentgames:
            currentgame = currentgames[currentgame_botname]
            #print("str for", currentgame)
            currentgame.msgstr = "Game hosted on " + currentgame.botname + " [" + currentgame.country + "]: `" + currentgame.gamename + "`\t(" + currentgame.players + ")"
        for disappearedgame in disappearedgames:
            disappearedgame.msgstr = "Game started (or cancelled): `" + disappearedgame.gamename + "` with " + disappearedgame.players + "!"

    def process_changes(self, new_open_games):
        #print("Process changes for: ", "last games", self.last_open_games, "new games", new_open_games)
        current_open_games = {}
        disappeared_games = []

        for new_botname in new_open_games:
            if new_botname in self.last_open_games.keys():
                # we have already seen this game last update
                oldgame = self.last_open_games[new_botname]
                newgame = new_open_games[new_botname]
                assert isinstance(oldgame, OpenGame)
                assert isinstance(newgame, OpenGame)
                newgame.previous = oldgame
                newgame.update_values_from(oldgame)
                newgame.status = SAMEGAME
                current_open_games[new_botname] = newgame
            else:
                # this is a new game
                current_open_games[new_botname] = new_open_games[new_botname]
                current_open_games[new_botname].status = NEWGAME

        for last_botname in self.last_open_games:
            if last_botname not in new_open_games.keys():
                # this game was open last time but is not open now
                self.last_open_games[last_botname].status = DISAPPEAREDGAME
                disappeared_games.append(self.last_open_games[last_botname])

        self.last_open_games = current_open_games
        self.fill_in_strings(current_open_games, disappeared_games)
        return current_open_games, disappeared_games

    def parse_html(self, html_doc):
        # work around VERY broken html before the ent games
        for _ in range(50):  # TODO: Fix this until there aren't </tr></tr> left
            html_doc = html_doc.replace("</tr></tr>", "</tr>")
        html_doc = html_doc.replace(" </tr><tr><td>Ent", "<tr><td>Ent")
        #print(html_doc)
        soup = BeautifulSoup(html_doc, 'html.parser')
        divs = soup.find('div', {"class": "refreshMeMMH"})
        rows = divs.table.find_all('tr')

        table_games = {}
        for row in rows:
            data = row.find_all("td")
            botname =  data[0].get_text()
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

    def get_evotag_games(self):
        table_games = self.parse_html(self.get_makemehost_as_str())
        return self.process_changes(table_games)

EDITMODE = "EDIT"
PRINTMODE = "PRINT"

if __name__ == "__main__":
    r = Requester()
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