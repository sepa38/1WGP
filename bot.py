import os
import discord


RAISED_HAND = "\N{Raised Hand}"
participationMessage = None

try:
    with open("TOKEN.txt", mode = "r") as f:
        TOKEN = f.read()
except:
    print("bot のトークンを TOKEN.txt に書き込んでください")
    exit()

try:
    with open("ONGOING.txt", mode = "r") as f:
        isOngoing = int(f.read())
except:
    isOngoing = 0
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


@client.event
async def on_message(message):
    global HOME_CHANNEL_ID, isOngoing, participationMessage, participant_list

    if not message.content.startswith("!"):
        return

    elif message.content.startswith("!set_home_channel"):
        HOME_CHANNEL_ID = message.channel.id

        with open("HOME_CHANNEL_ID.txt", mode = "w") as f:
            f.write(str(HOME_CHANNEL_ID))

        await message.channel.send("このチャンネルを 1WGP のホームチャンネルに設定しました")

    elif HOME_CHANNEL_ID is None:
        await message.channel.send("```\n!set_home_channel\n```でホームチャンネルを設定してください")

    elif message.content.startswith("!new_game"):
        if isOngoing:
            await message.channel.send("現在進行中のゲームがあるようです。新しくゲームを始める場合、 \
                ```\n!cancel_game\n```\nを用いて進行中のゲームを中断してください")
        else:
            participationMessage = await message.channel.send(f"参加希望者はこのメッセージに {RAISED_HAND} のリアクションをつけてください")
            await participationMessage.add_reaction(RAISED_HAND)
            participant_list = []

            isOngoing = 1
            with open("ONGOING.txt", mode = "w") as f:
                f.write(str(isOngoing))

    elif message.content.startswith("!confirm"):
        if isOngoing:
            participant_mention_list = [participant_i.mention for participant_i in participant_list]
            confirm_message = "以下のメンバーでゲームを開始します\n" + "\n".join(participant_mention_list)
            await message.channel.send(confirm_message)
            
            # TODO: 順番のシャッフルとか諸々の生成
        else:
            await message.channel.send("```\n!new_game\n```\nを用いてゲーム参加者を募集してください")

    elif message.content.startswith("!cancel_game"):
        isOngoing = 0
        with open("ONGOING.txt", mode = "w") as f:
            f.write(str(isOngoing))

        await message.channel.send("現在進行中のゲームを中断しました")

    elif message.content.startswith("!send_subject"):
        pass # TODO: 

    elif message.content.startswith('!send_picture'):
        save_path = "" # TODO: {ゲームを開始した日付}/{今のターン}/{参加者 ID} のようにする

        attachment = message.attachments[0]
        file_name = os.path.join(save_path, attachment.filename)
        await attachment.save(file_name) # とりあえず保存するところまで

    else:
        await message.channel.send("定義されていないコマンドです")


@client.event
async def on_reaction_add(reaction, user):
    global participationMessage, participant_list

    message = reaction.message
    category = message.channel.category
    channel_name = user.display_name

    if participationMessage is None:
        return

    if message != participationMessage or user == client.user:
        return

    participant_list.append(user)

    # 目的のチャンネルがすでに作られているとき
    channel_name_list = [channel_i.name for channel_i in category.text_channels]
    if channel_name in channel_name_list:
        return

    # プライベートチャンネルに設定するための dict
    permission = {
        message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True)
    }

    channel = await category.create_text_channel(name=channel_name, overwrites=permission)

    await channel.send("このチャンネルで画像、テキストの送受信をしてください")


client.run(TOKEN)