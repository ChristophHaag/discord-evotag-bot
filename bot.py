import traceback

import discord
import sys

import time

import os

debugarg = False
if len(sys.argv) > 1 and sys.argv[1] == "--debug":
    debugarg = True

import mmh
import asyncio

import ent_hosting

with open("token.txt", "r") as tokenfile:
    TOKEN = tokenfile.read().rstrip()
#print("Token: " + TOKEN)

client: discord.Client = discord.Client()

if mmh.DEBUG or debugarg:
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
        lines = f.readlines()
    newlines = [n for n in lines if not n.rstrip() == nick]
    deleted = len(newlines) != len(lines)
    if deleted:
        with open("subscriptions.txt", "w") as f:
            f.write("\n".join(newlines))
    return deleted


async def message_subscribed(msg):
    with open("subscriptions.txt", "r") as f:
        lines = [line for line in f.readlines() if line.rstrip()]

    server: discord.Server = list(client.servers)[0]
    members = {m.nick: m for m in server.members}
    for line in lines:
        if line.rstrip() in members.keys():
            author = members[line.rstrip()]
            await client.send_message(author, msg)


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await client.send_message(message.channel, msg)

    #if message.content.startswith('!test_subscription'):
    #    await message_subscribed("test123")

    if message.content.startswith('!subscribe'):
        if not os.path.exists("subscriptions.txt"): open("subscriptions.txt", 'a').close()
        author = message.author
        with open("subscriptions.txt", "r") as f:
            lines = f.readlines()
        if already_exists(lines, author.nick):
            await client.send_message(message.channel, '{0.author.mention} was already subscribed!'.format(message))
        else:
            lines.append(author.nick)
            with open("subscriptions.txt", "w") as f:
                f.write("\n".join(lines))
                await client.send_message(message.channel, '{0.author.mention} is now subscribed!'.format(message))
                await client.send_message(author, "Hello {0.author.mention}, you are now subscribed and will be messaged when games start and close. To unsubscribe, type !unsubscribe".format(message))

    if message.content.startswith('!unsubscribe'):
        deleted = delete_if_exists(message.author.nick)
        if deleted:
            await client.send_message(message.channel, '{0.author.mention} has unsubscribed!'.format(message))
            await client.send_message(message.author, "Hello {0.author.mention}, you are now unsubscribed. To subscribe again, type !subscribe".format(message))
        else:
            await client.send_message(message.channel, '{0.author.mention} was not subscribed!'.format(message))
    if message.content == ('!help ent'):
        msg = "Ingame commands: http://wiki.entgaming.net/index.php?title=EntGaming:HostGuide#Commands"
        await client.send_message(message.channel, msg)

    if message.content.startswith('!remove '):
        roles = message.author.roles
        authorized = False
        authorized_roles = ["Admin", "Bot Administrator", "Moderator"]
        roles_str = "[" + ", ".join(authorized_roles) + "]"
        for role in roles:
            if role.name in authorized_roles:
                authorized = True
        if not authorized:
            await client.send_message(message.channel, "User " + message.author.nick + " not authorized to remove messages! Only roles " + roles_str + " can remove messages!")
            return
        spl = message.content.split()
        if len(spl) > 1:
            numstr = spl[1]
            try:
                num = int(numstr)
            except ValueError:
                print("Clear: wrong value " + numstr)
                return
        msgs = client.logs_from(message.channel, limit=num + 1, before=None, after=None, around=None, reverse=False)
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
            await client.send_message(message.channel, msg)
            msg = "Note: It can take a few minutes until the ENT bot hosts the game and you can join."
            await client.send_message(message.channel, msg)
        else:
            msg = 'Host a game with !host <YOUR WARCRAFT ACCOUNT>'
            await client.send_message(message.channel, msg)


@client.event
async def on_ready():
    global channelid
    global channelobject
    print('Logged in as "' + client.user.name + '" (' + client.user.id + ")")
    print("Available Channels:")
    for server in client.servers:
        for channel in server.channels:
            print(channel.name + " " + channel.id)
            if channel.name == channelname:
                channelid = channel.id
                channelobject = client.get_channel(channelid)

    if not channelid:
        print("Error: Channel " + channelname + " not found!")
        return

    #print("Printing test to ", channelname, channelid, chan)
    #await client.send_message(chan, "test")

    r = mmh.Requester(debugarg)

    if mmh.DEBUG:
        mmh.INTERVAL = 3

    async def my_background_task():
        await client.wait_until_ready()

        loopcnt = 0
        while not client.is_closed:
            try:
                while not r.has_game_updates():
                    await asyncio.sleep(1)
                currentgames, disappearedgames = r.get_evotag_games()
                for botname, currentgame in currentgames.items():
                    assert(isinstance(currentgame, mmh.OpenGame))
                    if currentgame.status == mmh.NEWGAME:
                        currentgame.msgobj = await client.send_message(channelobject, currentgame.msgstr)
                        await message_subscribed("evo tag game got hosted: {}".format(currentgame.gamename))
                        print("New line: " + currentgame.msgstr, currentgame.msgobj)
                    elif currentgame.status == mmh.SAMEGAME:
                        print("Editing msg: " + currentgame.msgstr, currentgame.msgobj)
                        currentgame.msgobj = await client.edit_message(currentgame.msgobj, currentgame.msgstr)
                for disappearedgame in disappearedgames:
                    # first alter the old message from [OPEN] to [CLOSED]
                    disappearedgame.msgobj = await client.edit_message(disappearedgame.msgobj, disappearedgame.msgobj.content.replace("[OPEN]", "[CLOSED]"))
                    print("New line: " + disappearedgame.msgstr)
                    await client.send_message(channelobject, disappearedgame.msgstr)
                    await client.send_message(channelobject, "-----------------------------------------------")
                    await message_subscribed("evo tag game started: {}".format(disappearedgame.gamename))
                loopcnt += 1
            except Exception as e:
                print("Exception happened!", e)
                traceback.print_exc()

    client.loop.create_task(my_background_task())


def run_client(c, *args, **kwargs):
    loop = asyncio.get_event_loop()
    while True:
        try:
            loop.run_until_complete(c.start(*args, **kwargs))
        except Exception as e:
            print("Error", e)
        print("Waiting until restart")
        time.sleep(10)


# client.run(TOKEN)  # https://stackoverflow.com/a/49082260
run_client(client, TOKEN)
