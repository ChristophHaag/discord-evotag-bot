from bs4 import BeautifulSoup
import re
import urllib.request
import time
import threading

DEBUG = False

class Requester():
    cb = None
    running = True
    lastnames = set()
    def __init__(self, cb):
        pass

    def abort(self):
        self.running = False

    def manual_loop(self):
        return self.get_evotag_games()

    def get_mmh_str(self):
        if DEBUG:
            with open("website.html", "r") as f:
                html_doc = f.read()
        else:
            URL = "http://makemehost.com/games.php"
            html_doc = urllib.request.urlopen(URL).read().decode("utf8")
        return html_doc

    def found_game(self, gns):
        if gns == self.lastnames:
            print("Game status has not changed")
        else:
            self.lastnames = gns
            return gns


    def get_evotag_games(self):
        html_doc = self.get_mmh_str()
        #print(html_doc)

        soup = BeautifulSoup(html_doc, 'html.parser')
        divs = soup.find('div', { "class": "refreshMeMMH" } )
        rows = divs.table.find_all('tr')

        found_games = set()
        for row in rows:
            data = row.find_all("td")
            gn = data[3].get_text()
            players = data[4].get_text()
            #print(gn)
            m = re.search('.*evo.*tag.*', gn.lower())
            #print(m)
            if m:
                found_games.add((gn, players))
        for g in found_games:
            #print("found " + str(g))
            pass
        if len(found_games) > 0:
            return self.found_game(found_games)

def cb(gns):
    msg = ""
    for i, gn in enumerate(gns):
        msg += "Gamename: `"+ gn[0]+"`   ("+gn[1]+")"
        if (i < len(gns) - 1):
            msg += "\n"
    print(msg)

if __name__ == "__main__":
    r = Requester(cb)
    print(r.manual_loop())
    time.sleep(1)
    print(r.manual_loop())
