import time
from bs4 import BeautifulSoup
import re
import urllib.request

DEBUG = False
# debug returns: None, 5/12, 6/12, 6/12, 7/12, None, None, 5/12 + 5/12, 5/12 + 6/12, 5/12 + 6/12, 6/12, None
debugsites = ["websitewithout.html", "websitewith5-12.html", "websitewith6-12.html", "websitewith6-12.html", "websitewith7-12.html", "websitewithout.html", "websitewithout.html", "websitewithdouble5-12.html", "websitewithdouble6-12.html", "websitewithdouble6-12.html", "websitewith6-12.html", "websitewithout.html"]
DISAPPEARED = "DISAPPEARED"
SAME = "SAME"

class Requester():
    cb = None
    running = True
    lastnames = []
    requestscount = 0

    def __init__(self):
        pass

    def abort(self):
        self.running = False

    def get_mmh_str(self):
        if DEBUG:
            num = self.requestscount % (len(debugsites) - 1)
            with open(debugsites[num], "r") as f:
                #print("Debug: opening " + str(num) + ": " + f.name)
                html_doc = f.read()
        else:
            URL = "http://makemehost.com/games.php"
            html_doc = urllib.request.urlopen(URL).read().decode("utf8")
        self.requestscount += 1
        return html_doc

    def found_game(self, gns):
        #print("Found game: " + str(gns) + ", " + str(self.lastnames))
        if len(gns) == 0 and len(self.lastnames) > 0:
            self.lastnames = gns
            return DISAPPEARED
        if gns == self.lastnames:
            #print("Game status has not changed")
            return SAME
        else:
            self.lastnames = gns
            return gns

    def get_evotag_games(self):
        """returns a list of string tuples [(gamename, players), (...)] or the constants DISAPPEARED or SAME"""
        html_doc = self.get_mmh_str()
        #print(html_doc)

        soup = BeautifulSoup(html_doc, 'html.parser')
        divs = soup.find('div', {"class": "refreshMeMMH"})
        rows = divs.table.find_all('tr')

        found_games = []
        for row in rows:
            data = row.find_all("td")
            gn = data[3].get_text()
            players = data[4].get_text()
            #print(gn)
            m = re.search('.*evo.*tag.*', gn.lower())
            #print(m)
            if m:
                found_games.append((gn, players))
        for g in found_games:
            #print("found " + str(g))
            pass
        return self.found_game(found_games)

def makeString(gns):
    msg = ""
    if gns == SAME:
        msg = None
    elif gns == DISAPPEARED:
        msg = "Game started or cancelled!"
    else:
        # TODO: 1/2 games are started
        for i, gn in enumerate(gns):
            if len(gns) > 1:
                nums = " (" + str(i+1) + "/" + str(len(gns)) + ")"
            else:
                nums = ""
            msg += "Gamename" + nums + " : `" + gn[0] + "`   (" + gn[1] + ")"
            if (i < len(gns) - 1):
                msg += "\n"
    return msg


if __name__ == "__main__":
    r = Requester()
    rnum = len(debugsites) if DEBUG else 5
    for i in range(rnum):
        gns = r.get_evotag_games()
        s = makeString(gns)
        prefix = "Request " + str(i) + ": "
        if s:
            print(prefix + s.replace("\n", "\n" + prefix))
            if not DEBUG:
                time.sleep(5)
        else:
            print(prefix + "<No changes>")
