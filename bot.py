import discord
import mmh
import asyncio

with open("token.txt", "r") as tokenfile:
    TOKEN = tokenfile.read().rstrip()
#print("Token: " + TOKEN)

client = discord.Client()

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


@client.event
async def on_ready():
    global channelid
    global channelobject
    print('Logged in as' + client.user.name + "(" + client.user.id + ")")
    print("Available Channels:")
    for server in client.servers:
        for channel in server.channels:
            print(channel.name + " "  + channel.id)
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
        while not client.is_closed:
            gns = r.get_evotag_games()
            msg = mmh.makeString(gns)
            if msg:
                await client.send_message(channelobject, msg)
            await asyncio.sleep(15)  # task runs every X seconds
    client.loop.create_task(my_background_task())

client.run(TOKEN)
