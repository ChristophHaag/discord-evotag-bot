import discord
import mmh
import asyncio

with open("token.txt", "r") as tokenfile:
    TOKEN = tokenfile.read().rstrip()
#print("Token: " + TOKEN)

client = discord.Client()

channelname = "hosted-games"
channelid = None
chan = None

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
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    print("channels:")
    for server in client.servers:
        for channel in server.channels:
            print(channel.name + " "  + channel.id)
            if channel.name == channelname:
                channelid = channel.id
                chan = client.get_channel(channelid)

    if not channelid:
        print("Error: Channel " + channelname + " not found!")
        return

    #print("Printing test to ", channelname, channelid, chan)
    #await client.send_message(chan, "test")
    @client.event
    async def cb(gns):
        print("Open game found: " + str(gns))
        channel = client.get_channel("general")
        msg = ""
        for i, gn in enumerate(gns):
            msg += "Gamename: `"+ gn[0]+"`   ("+gn[1]+")"
            if (i < len(gns) - 1):
                msg += "\n"
        print(msg)
        client.send_message(chan, msg)
    r = mmh.Requester(cb)
    async def my_background_task():
        await client.wait_until_ready()
        while not client.is_closed:
            gns = r.manual_loop()
            if gns != None:
                if len(gns) == 0:
                    msg = "Game started!"
                msg = ""
                for i, gn in enumerate(gns):
                    msg += "Gamename: `"+ gn[0]+"`   ("+gn[1]+")"
                    if (i < len(gns) - 1):
                        msg += "\n"
                await client.send_message(chan, msg)
            await asyncio.sleep(15) # task runs every 60 seconds
    client.loop.create_task(my_background_task())

client.run(TOKEN)
