import traceback

import discord
import sys

import time

import os

debugarg = False
if len(sys.argv) > 1 and sys.argv[1] == "--debug":
    debugarg = True

import asyncio

import ent_hosting

with open("token.txt", "r") as tokenfile:
    TOKEN = tokenfile.read().rstrip()
#print("Token: " + TOKEN)

client = discord.Client()

if debugarg:
    channelname = "bot-test"
else:
    channelname = "hosted-games"  # channelid and channelobject will be filled in
channelid = None
channelobject = None


def already_exists(lines, nick):
    for line in lines:
        if line.rstrip().lstrip() == nick:
            return True
    return False


def delete_if_exists(nick):
    with open("subscriptions.txt", "r") as f:
        lines = [l for l in f.readlines() if l.rstrip()]
    newlines = [n for n in lines if not n.rstrip() == nick]
    deleted = len(newlines) != len(lines)
    if deleted:
        with open("subscriptions.txt", "w") as f:
            f.write("\n".join(newlines))
    return deleted


async def message_subscribed(msg):
    with open("subscriptions.txt", "r") as f:
        lines = [line for line in f.readlines() if line.rstrip()]

    members = {m.nick: m for m in client.get_all_members()}
    for line in lines:
        if line.rstrip() in members.keys():
            author = members[line.rstrip()]
            await author.send(msg)


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await message.channel.send(msg)

    #if message.content.startswith('!test_subscription'):
    #    await message_subscribed("test123")

    if message.content.startswith('!subscribe'):
        if not os.path.exists("subscriptions.txt"): open("subscriptions.txt", 'a').close()
        author = message.author
        with open("subscriptions.txt", "r") as f:
            lines = [l for l in f.readlines() if l.rstrip()]
        if already_exists(lines, author.nick):
            await message.channel.send('{0.author.mention} was already subscribed!'.format(message))
        else:
            lines.append(author.nick)
            with open("subscriptions.txt", "w") as f:
                f.write("\n".join(lines))
                await message.channel.send('{0.author.mention} is now subscribed!'.format(message))
                await author.send("Hello {0.author.mention}, you are now subscribed and will be messaged when games start and close. To unsubscribe, type !unsubscribe".format(message))

    if message.content.startswith('!unsubscribe'):
        deleted = delete_if_exists(message.author.nick)
        if deleted:
            await message.channel.send('{0.author.mention} has unsubscribed!'.format(message))
            await message.author.send("Hello {0.author.mention}, you are now unsubscribed. To subscribe again, type !subscribe".format(message))
        else:
            await message.channel.send('{0.author.mention} was not subscribed!'.format(message))
    if message.content == ('!help ent'):
        msg = "Ingame commands: http://wiki.entgaming.net/index.php?title=EntGaming:HostGuide#Commands"
        await message.channel.send(msg)

    if message.content.startswith('!remove '):
        await message.channel.send("Currently disabled")
        return
        roles = message.author.roles
        authorized = False
        authorized_roles = ["Admin", "Bot Administrator", "Moderator"]
        roles_str = "[" + ", ".join(authorized_roles) + "]"
        for role in roles:
            if role.name in authorized_roles:
                authorized = True
        if not authorized:
            await message.channel.send("User " + message.author.nick + " not authorized to remove messages! Only roles " + roles_str + " can remove messages!")
            return
        spl = message.content.split()
        if len(spl) > 1:
            numstr = spl[1]
            try:
                num = int(numstr)
            except ValueError:
                print("Clear: wrong value " + numstr)
                return
        msgs = message.channel.logs_from(limit=num + 1, before=None, after=None, around=None, reverse=False)
        #print("Messages to clear: ", msgs)
        print("Delete messages:")
        first = True
        async for msg in msgs:
            if first:
                first = False
                continue
            await client.delete_message(msg)
            print("[deleted]", msg.content)

    if message.content.startswith('!host'):
        if not ent_hosting.logged_in:
            ent_hosting.login()
        spl = message.content.split(" ")
        if len(spl) == 2:
            gamename = ent_hosting.host_game(spl[1])
            msg = "Game hosted with game name `" + gamename + "`. After joining in Warcraft change the name with `!pub <GAME NAME>` and start the game with `!start`."
            await message.channel.send(msg)
            msg = "Note: It can take a few minutes until the ENT bot hosts the game and you can join."
            await message.channel.send(msg)
        else:
            msg = 'Host a game with !host <YOUR WARCRAFT ACCOUNT>'
            await message.channel.send(msg)


task_created = False

import json
import urllib.request

def get_gamelist_json():
    j = None
    if debugarg:
        with open("gamelist.json", "r") as f:
            j = json.load(f)
    else:
        url = "https://api.wc3stats.com/gamelist"
        try:
            resp = urllib.request.urlopen(url).read().decode("utf8", errors="replace")
            j = json.loads(resp)
        except urllib.error.URLError as e:
            print("urlopen error", e)
            return ""
        except Exception as e:
            print("urlopen exception", e)
            return ""
    #print("json ", j)
    return j


current_games = dict()


def is_evo_tag(json):
    res = json["map"].startswith("Evolution Tag")
    #print("Is evo tag:", json["map"], res)
    return res

def is_new(json):
    return json["id"] not in current_games.keys()

def game_to_msgstr(json):
    res = "{} - {} [{}/{}] - {} [Server: {}]".format(json["name"], json["map"], json["slotsTaken"], json["slotsTotal"], json["host"], json["server"])
    return res

def get_started_games(json):
    res = []
    json_ids = []

    for jgame in json["body"]:
        if (is_evo_tag(jgame)):
            json_ids.append(jgame["id"])
    for game_id in current_games.keys():
        if game_id not in json_ids:
            res.append(current_games[game_id])
    return res

@client.event
async def on_ready():
    global channelid
    global channelobject
    print('Logged in as "' + client.user.name + '" (' + str(client.user.id) + ")")
    print("Available Channels:")
    for channel in client.get_all_channels():
        print(channel.name + " " + str(channel.id))
        if channel.name == channelname:
            channelid = channel.id
            channelobject = client.get_channel(channelid)

    if not channelid:
        print("Error: Channel " + channelname + " not found!")
        return

    #print("Printing test to ", channelname, channelid, chan)
    #await chan.send("test")

    async def my_background_task():
        await client.wait_until_ready()

        loopcnt = 0
        while True:
            try:
                j = get_gamelist_json()
                #print("Read", j)


                for jgame in j["body"]:
                    if is_evo_tag(jgame):
                        msgstr = "[OPEN] " + game_to_msgstr(jgame)
                        if is_new(jgame):
                            print("New Evo tag, ", jgame)
                            current_games[jgame["id"]] = jgame

                            print("Posting message {}".format(msgstr))

                            jgame["prev_msgstr"] = msgstr

                            jgame["msgobj"] = await channelobject.send(msgstr)
                            await message_subscribed("evo tag game got hosted: {}".format(msgstr))
                        else:
                            prev_msg = current_games[jgame["id"]]["prev_msgstr"]
                            #print("prev {}, new {}".format(prev_msg, msgstr)
                            if prev_msg == msgstr:
                                #print("Message did not change {}".format(msgstr))
                                continue
                            print("Editing msg: " + msgstr, current_games[jgame["id"]]["msgobj"])
                            await current_games[jgame["id"]]["msgobj"].edit(content=msgstr)
                            current_games[jgame["id"]]["prev_msgstr"] = msgstr

                started_games = get_started_games(j)
                for started_game in started_games:
                    # first alter the old message from [OPEN] to [CLOSED]
                    msgstr = "[STARTED] " + game_to_msgstr(started_game)
                    await started_game["msgobj"].edit(content=msgstr)
                    #await channelobject.send(msgstr)
                    #await channelobject.send("-----------------------------------------------")
                    await message_subscribed("evo tag game started: {}".format(msgstr))
                    print("Started game {}", started_game)
                    del current_games[started_game["id"]]
                await asyncio.sleep(10)

            except Exception as e:
                print("Exception happened!", e)
                traceback.print_exc()
                await asyncio.sleep(10)


    global task_created
    if not task_created:
        client.loop.create_task(my_background_task())
        task_created = True
    else:
        print("ERROR: TRYING TO CREATE A SECOND TASK WITH NO REASON TO DO SO")


def run_client(c, *args, **kwargs):
    loop = asyncio.get_event_loop()
    try:
        print("Running bot main loop")
        loop.run_until_complete(c.start(*args, **kwargs))
    except Exception as e:
        loop.stop()
        while loop.is_running():
            print("Waiting for event loop to stop...")
            time.sleep(1)
        loop.close()
        print("Error", e)

# client.run(TOKEN)  # https://stackoverflow.com/a/49082260
while (True):
    run_client(client, TOKEN)
    client.close()
    print("Waiting until restart")
    time.sleep(10)
    client = discord.Client()
