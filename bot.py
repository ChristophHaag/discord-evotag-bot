import discord
import mmh
import asyncio

import ent_hosting

with open("token.txt", "r") as tokenfile:
    TOKEN = tokenfile.read().rstrip()
#print("Token: " + TOKEN)

client = discord.Client()

if mmh.DEBUG:
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

    if message.content.startswith('!host'):
        if not ent_hosting.logged_in:
            ent_hosting.login()
        spl = message.content.split(" ")
        if len(spl) == 2:
            gamename = ent_hosting.host_game(spl[1])
            msg = "Game hosted with game name `" + gamename + "`. Once having joined the game in Warcraft, change the game name with `!pub <GAME NAME>`."
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

    r = mmh.Requester()

    async def my_background_task():
        await client.wait_until_ready()

        loopcnt = 0
        while not client.is_closed:
            currentgames, disappearedgames = r.get_evotag_games()
            for botname, currentgame in currentgames.items():
                if currentgame.status == mmh.NEWGAME:
                    currentgame.userptr = await client.send_message(channelobject, currentgame.msgstr)
                    print("New line: " + currentgame.msgstr, currentgame.userptr)
                elif currentgame.status == mmh.SAMEGAME:
                    print("Editing msg: " + currentgame.msgstr, currentgame.userptr)
                    currentgame.userptr = await client.edit_message(currentgame.userptr, currentgame.msgstr)
            for disappearedgame in disappearedgames:
                print("New line: " + disappearedgame.msgstr)
                await client.send_message(channelobject, disappearedgame.msgstr)
            loopcnt += 1
            if mmh.DEBUG:
                interval = 1
            else:
                interval = 15
            await asyncio.sleep(interval)  # task runs every X seconds
    client.loop.create_task(my_background_task())

client.run(TOKEN)
