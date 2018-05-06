#!/usr/bin/env python3

import requests
import pickle
from bs4 import BeautifulSoup

DEBUG = False

cookiefile = "cookies.bin"
headers = {'User-Agent': 'Mozilla/5.0'}
session = requests.Session()

logged_in = False

def save_cookies(requests_cookiejar, filename):
    with open(filename, 'wb') as f:
        pickle.dump(requests_cookiejar, f)


def load_cookies(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)


def login():
    global logged_in
    with open("usernamepassword.txt", "r") as f:
        username = f.readline().rstrip()
        password = f.readline().rstrip()
    print("username", username)
    print("password", password)

    loginurl = "https://entgaming.net/forum/"
    payload = {'username': username, 'password': password, 'redirect': 'index.php', 'sid': '', 'login': 'Login'}

    print("Logging into ENT...")
    loginresponse = session.post(loginurl + "ucp.php?mode=login", headers=headers, data=payload)
    print("Logged in...")
    with open("login_reply.html", "w") as f:
        # print(loginresponse.text)
        #f.write(loginresponse.text)
        pass
    # logged_in = True # //TODO: session times out eventually
    save_cookies(loginresponse.cookies, cookiefile)


def get_gamename_from_ent_html(html_doc):
    soup = BeautifulSoup(html_doc, 'html.parser')
    p = soup.find('p', {"class": "donate"}).getText()
    secondhalf = p.split("GAMENAME: ")[1]
    firsthalf = secondhalf.split("Note: ")[0]
    #print(firsthalf)
    return firsthalf


def host_game(owner):
    hosturl = "https://entgaming.net/link/host.php"
    data = {"location": "europe", "map": ":kald0", "owner": owner, "private": "false"}
    print("Hosting game...")
    r = session.post(hosturl, headers=headers, data=data)
    with open("ent_reply.html", "w") as f:
        #print(r.text)
        #f.write(r.text)
        pass
    gamename = get_gamename_from_ent_html(r.text)
    print("Hosted game with name..." + gamename)
    return gamename


if __name__ == "__main__":
    if DEBUG:
        with open("ent_reply.html", "r") as f:
            html = f.read()
            gamename = get_gamename_from_ent_html(html)
    else:
        gamename = host_game("Dark_Werewolf")
    print("Gamename: " + gamename)
