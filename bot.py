import os
import datetime
import random
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
    # HACK: 後でクラスにまとめる
    global HOME_CHANNEL_ID, isOngoing, participationMessage, participant_list, individualChannelList, currentTurn, completedUsers

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
            individualChannelList = []
            completedUsers = set()

            isOngoing = 1
            with open("ONGOING.txt", mode = "w") as f:
                f.write(str(isOngoing))

    elif message.content.startswith("!confirm"):
        if isOngoing:
            participant_mention_list = [participant_i.mention for participant_i in participant_list]
            confirm_message = "以下のメンバーでゲームを開始します\n" + "\n".join(participant_mention_list)
            await message.channel.send(confirm_message)
            
            participant_ID_list = [str(participant_i.id) for participant_i in participant_list]
            with open("participants_ID_list.txt", mode = "w") as f:
                f.write(" ".join(participant_ID_list))

            startDate = str(datetime.datetime.now().replace(microsecond=0))
            startDate = startDate.replace(" ", "_").replace(":", "-")
            os.mkdir(startDate)

            numberOfParticipants = len(participant_list)
            for turn in range(numberOfParticipants):
                for user_index in range(numberOfParticipants):
                    os.makedirs(f"{startDate}/{turn}/{user_index}")

            passingTable = [[] for i in range(numberOfParticipants)]
            for turn in range(numberOfParticipants):
                for user_index in range(numberOfParticipants):
                    user_tmp = participant_list[(turn+user_index)%numberOfParticipants]
                    passingTable[turn].append(user_tmp)
            random.shuffle(passingTable)

            passingTableForSave = []
            for turn in range(numberOfParticipants):
                turnUsers = [str(user_tmp.id) for user_tmp in passingTable[turn]]
                passingTableForSave.append(" ".join(turnUsers))
            with open("passing_table.txt", mode = "w") as f:
                f.write("\n".join(passingTableForSave))

        else:
            await message.channel.send("```\n!new_game\n```\nを用いてゲーム参加者を募集してください")

    elif message.content.startswith("!cancel_game"):
        isOngoing = 0
        with open("ONGOING.txt", mode = "w") as f:
            f.write(str(isOngoing))

        await message.channel.send("現在進行中のゲームを中断しました")

    elif message.content.startswith("!send_subject"):
        if message.channel not in individualChannelList:
            return

        if not isOngoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if currentTurn % 2 == 1:
            await message.channel.send("現在、絵を送信するフェーズです。\n```\n!send_picture\n```\nを用いて画像を送信してください")
            return
        
        userIndex = participant_ID_list.index(message.author.id)
        targetPath = os.path.join(startDate, str(currentTurn))
        targetPath = os.path.join(targetPath, str(userIndex))
        with open(os.path.join(targetPath, "subject.txt")) as f:
            f.write(message.content) # FIXME: !send_subject ごと書き込まれる

        completedUsers.add(message.author.id)
        if len(completedUsers) == numberOfParticipants:
            pass
            # next_job() TODO: send_picture とまとめる

    elif message.content.startswith('!send_picture'):
        if message.channel not in individualChannelList:
            return

        if not isOngoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if currentTurn % 2 == 0:
            await message.channel.send("現在、お題もしくは絵の説明を送信するフェーズです。\n```\n!send_subject\n```\nを用いて文章を送信してください")
            return

        userIndex = participant_ID_list.index(message.author.id)
        targetPath = os.path.join(startDate, str(currentTurn))
        targetPath = os.path.join(targetPath, str(userIndex))

        attachment = message.attachments[0]
        fileName = os.path.join(targetPath, attachment.filename)
        await attachment.save(fileName)
        
        completedUsers.add(message.author.id)
        if len(completedUsers) == numberOfParticipants:
            pass
            # next_job() TODO: send_subject とまとめる

    else:
        await message.channel.send("定義されていないコマンドです")


@client.event
async def on_reaction_add(reaction, user):
    global participationMessage, participant_list, individualChannelList

    message = reaction.message
    category = message.channel.category
    channel_name = user.name

    if participationMessage is None:
        return

    if message != participationMessage or user == client.user:
        return

    participant_list.append(user)

    # 目的のチャンネルがすでに作られているとき
    for channel_i in category.text_channels:
        if channel_name == channel_i.name:
            individualChannelList.append(channel_i)
            return

    # プライベートチャンネルに設定するための dict
    permission = {
        message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True)
    }

    channel = await category.create_text_channel(name=channel_name, overwrites=permission)

    individualChannelList.append(channel)

    await channel.send("このチャンネルで画像、テキストの送受信をしてください")


@client.event
async def on_reaction_remove(reaction, user):
    global participationMessage, participant_list

    message = reaction.message

    if participationMessage is None:
        return

    if message != participationMessage or user == client.user:
        return

    participant_list.remove(user)


client.run(TOKEN)