import discord


client = discord.Client(intents=discord.Intents.all())

with open("TOKEN.txt", mode = "r") as f:
    TOKEN = f.read()

client.run(TOKEN)