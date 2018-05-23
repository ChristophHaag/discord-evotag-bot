import traceback

import discord
import sys

debugarg = False
if len(sys.argv) > 1 and sys.argv[1] == "--debug":
    debugarg = True

import mmh
import asyncio

import ent_hosting

with open("token.txt", "r") as tokenfile:
    TOKEN = tokenfile.read().rstrip()
#print("Token: " + TOKEN)

client = discord.Client()

if mmh.DEBUG or debugarg:
    channelname = "bot-test"
else:
    channelname = "hosted-games"  # channelid and channelobject will be filled in
channelid = None
channelobject = None


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await client.send_message(message.channel, msg)

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
                        print("New line: " + currentgame.msgstr, currentgame.msgobj)
                    elif currentgame.status == mmh.SAMEGAME:
                        print("Editing msg: " + currentgame.msgstr, currentgame.msgobj)
                        currentgame.msgobj = await client.edit_message(currentgame.msgobj, currentgame.msgstr)
                for disappearedgame in disappearedgames:
                    print("New line: " + disappearedgame.msgstr)
                    await client.send_message(channelobject, disappearedgame.msgstr)
                    await client.send_message(channelobject, "-----------------------------------------------")
                loopcnt += 1
            except Exception as e:
                print("Exception happened!", e)
                traceback.print_exc()

    client.loop.create_task(my_background_task())

client.run(TOKEN)
