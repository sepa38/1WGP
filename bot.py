import discord


RAISED_HAND = "\N{Raised Hand}"
NEW_GAME_MESSAGE = f"参加希望者はこのメッセージに {RAISED_HAND} のリアクションをつけてください"

try:
    with open("TOKEN.txt", mode = "r") as f:
        TOKEN = f.read()
except:
    print("bot のトークンを TOKEN.txt に書き込んでください")
    exit()

try:
    with open("ONGOING.txt", mode = "r") as f:
        isOngoing = bool(f.read())
except:
    isOngoing = False
    with open("ONGOING.txt", mode = "w") as f:
        f.write(str(isOngoing))

try:
    with open("HOME_CHANNEL_ID.txt", mode = "r") as f:
        HOME_CHANNEL_ID = int(f.read())
except:
    HOME_CHANNEL_ID = None


client = discord.Client(intents=discord.Intents.all())


@client.event
async def on_ready():
    print("Successfully activated")


client.run(TOKEN)