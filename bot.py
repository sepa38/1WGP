import os
import datetime
import random

import discord
from discord.ext import tasks


RAISED_HAND = "\N{Raised Hand}"
participation_message = None

try:
    with open("TOKEN.txt", mode = "r") as f:
        TOKEN = f.read()
except:
    print("bot のトークンを TOKEN.txt に書き込んでください")
    exit()

try:
    with open("ongoing.txt", mode = "r") as f:
        is_ongoing = int(f.read())
except:
    is_ongoing = 0
    with open("ongoing.txt", mode = "w") as f:
        f.write(str(is_ongoing))

try:
    with open("home_channel_id.txt", mode = "r") as f:
        HOME_CHANNEL_ID = int(f.read())
except:
    HOME_CHANNEL_ID = None


client = discord.Client(intents=discord.Intents.all())


async def next_job():
    global participant_list, individual_channel_list, passing_table, current_turn, number_of_participants, HOME_CHANNEL_ID, start_date, is_ongoing, completed_users, deadline
    if current_turn == number_of_participants - 1:
        home_channel = client.get_channel(HOME_CHANNEL_ID)
        await home_channel.send("ゲームが終了しました")
        
        for game_index in range(number_of_participants):
            first_participant = passing_table[0][game_index]
            message = await home_channel.send(f"{first_participant.name} のお題")
            thread = await message.create_thread(name = f"{first_participant.name} のお題")

            for turn in range(number_of_participants):
                target_path = os.path.join(start_date, str(turn), str(game_index))
                creator = passing_table[turn][game_index]

                if turn % 2 == 0:
                    with open(os.path.join(target_path, "subject.txt"), mode = "r") as f:
                        subject = f.read()
                    await thread.send(f"{creator.mention}\n{subject}")
                
                else:
                    file_name = os.listdir(target_path)[0]
                    await thread.send(f"{creator.mention}", file=discord.File(os.path.join(target_path, file_name)))

        is_ongoing = 0
        with open("ongoing.txt", mode = "w") as f:
            f.write(str(is_ongoing))

        return

    # send_subject が全員分揃ったとき
    if current_turn % 2 == 0:
        for game_index in range(number_of_participants):
            next_user = passing_table[current_turn+1][game_index]
            for destination_channel in individual_channel_list:
                if destination_channel.name == next_user.name:
                    break

            target_path = os.path.join(start_date, str(current_turn), str(game_index))
            with open(os.path.join(target_path, "subject.txt"), mode = "r") as f:
                subject = f.read()
            
            print(game_index, destination_channel.name, next_user.name, target_path)
            await destination_channel.send(f"次のお題について絵を描いてください\n```\n{subject}\n```")
        
        deadline = datetime.date.today() + datetime.timedelta(days=7)

    else:
        for game_index in range(number_of_participants):
            next_user = passing_table[current_turn+1][game_index]
            for destination_channel in individual_channel_list:
                if destination_channel.name == next_user.name:
                    break
            
            target_path = os.path.join(start_date, str(current_turn), str(game_index))
            file_name = os.listdir(target_path)[0]
            await destination_channel.send(f"次の絵の説明をしてください", file=discord.File(os.path.join(target_path, file_name)))
        
        deadline = datetime.date.today() + datetime.timedelta(days=1)

    completed_users = set()
    current_turn += 1
    return


@client.event
async def on_ready():
    print("Successfully activated")


@client.event
async def on_message(message):
    # HACK: 後でクラスにまとめる
    global HOME_CHANNEL_ID, is_ongoing, participation_message, participant_list, individual_channel_list, current_turn, completed_users, passing_table, number_of_participants, start_date, participant_id_list, individual_channel_list, deadline

    if not message.content.startswith("!"):
        return

    elif message.content.startswith("!set_home_channel"):
        HOME_CHANNEL_ID = message.channel.id

        with open("home_channel_id.txt", mode = "w") as f:
            f.write(str(HOME_CHANNEL_ID))

        await message.channel.send("このチャンネルを 1WGP のホームチャンネルに設定しました")

    elif HOME_CHANNEL_ID is None:
        await message.channel.send("```\n!set_home_channel\n```でホームチャンネルを設定してください")

    elif message.content.startswith("!new_game"):
        if is_ongoing:
            await message.channel.send("現在進行中のゲームがあるようです。新しくゲームを始める場合、 \
                ```\n!cancel_game\n```\nを用いて進行中のゲームを中断してください")
        else:
            participation_message = await message.channel.send(f"参加希望者はこのメッセージに {RAISED_HAND} のリアクションをつけてください")
            await participation_message.add_reaction(RAISED_HAND)
            participant_list = []
            individual_channel_list = []
            completed_users = set()
            current_turn = 0

            is_ongoing = 1
            with open("ongoing.txt", mode = "w") as f:
                f.write(str(is_ongoing))

    elif message.content.startswith("!confirm"):
        if is_ongoing:
            participant_mention_list = [participant_i.mention for participant_i in participant_list]
            confirm_message = "以下のメンバーでゲームを開始します\n" + "\n".join(participant_mention_list)
            await message.channel.send(confirm_message)
            
            participant_id_list = [participant_i.id for participant_i in participant_list]
            id_list_str = [str(id_i) for id_i in participant_id_list]
            with open("participants_ID_list.txt", mode = "w") as f:
                f.write(" ".join(id_list_str))

            start_date = str(datetime.datetime.now().replace(microsecond=0))
            start_date = start_date.replace(" ", "_").replace(":", "-")
            os.mkdir(start_date)

            number_of_participants = len(participant_list)
            for turn in range(number_of_participants):
                for user_index in range(number_of_participants):
                    os.makedirs(f"{start_date}/{turn}/{user_index}")

            passing_table = [[] for i in range(number_of_participants)]
            for turn in range(number_of_participants):
                for user_index in range(number_of_participants):
                    user_tmp = participant_list[(turn+user_index)%number_of_participants]
                    passing_table[turn].append(user_tmp)
            random.shuffle(passing_table)

            passing_table_for_save = []
            for turn in range(number_of_participants):
                turn_users = [str(user_tmp.id) for user_tmp in passing_table[turn]]
                passing_table_for_save.append(" ".join(turn_users))
            with open("passing_table.txt", mode = "w") as f:
                f.write("\n".join(passing_table_for_save))
            
            deadline = datetime.date.today() + datetime.timedelta(days=7)

        else:
            await message.channel.send("```\n!new_game\n```\nを用いてゲーム参加者を募集してください")

    elif message.content.startswith("!cancel_game"):
        is_ongoing = 0
        with open("ongoing.txt", mode = "w") as f:
            f.write(str(is_ongoing))

        await message.channel.send("現在進行中のゲームを中断しました")

    elif message.content.startswith("!send_subject"):
        if message.channel not in individual_channel_list:
            return

        if not is_ongoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if current_turn % 2 == 1:
            await message.channel.send("現在、絵を送信するフェーズです。\n```\n!send_picture\n```\nを用いて画像を送信してください")
            return

        user_index = passing_table[current_turn].index(message.author)
        target_path = os.path.join(start_date, str(current_turn), str(user_index))
        with open(os.path.join(target_path, "subject.txt"), mode = "w") as f:
            f.write(message.content.replace("!send_subject", ""))

        completed_users.add(message.author.id)
        if len(completed_users) == number_of_participants:
            await next_job()

    elif message.content.startswith('!send_picture'):
        if message.channel not in individual_channel_list:
            return

        if not is_ongoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if current_turn % 2 == 0:
            await message.channel.send("現在、お題もしくは絵の説明を送信するフェーズです。\n```\n!send_subject\n```\nを用いて文章を送信してください")
            return

        user_index = passing_table[current_turn].index(message.author)
        target_path = os.path.join(start_date, str(current_turn), str(user_index))

        attachment = message.attachments[0]
        file_name = os.path.join(target_path, attachment.filename)
        await attachment.save(file_name)
        
        completed_users.add(message.author.id)
        if len(completed_users) == number_of_participants:
            await next_job()

    else:
        await message.channel.send("定義されていないコマンドです")


@client.event
async def on_reaction_add(reaction, user):
    global participation_message, participant_list, individual_channel_list

    message = reaction.message
    category = message.channel.category
    channel_name = user.name

    if participation_message is None:
        return

    if message != participation_message or user == client.user:
        return

    participant_list.append(user)

    # 目的のチャンネルがすでに作られているとき
    for channel_i in category.text_channels:
        if channel_name == channel_i.name:
            individual_channel_list.append(channel_i)
            return

    # プライベートチャンネルに設定するための dict
    permission = {
        message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True)
    }

    channel = await category.create_text_channel(name=channel_name, overwrites=permission)

    individual_channel_list.append(channel)

    await channel.send("このチャンネルで画像、テキストの送受信をしてください")


@client.event
async def on_reaction_remove(reaction, user):
    global participation_message, participant_list

    message = reaction.message

    if participation_message is None:
        return

    if message != participation_message or user == client.user:
        return

    participant_list.remove(user)


@tasks.loop(seconds=60)
async def daily_job():
    global deadline
    now = datetime.datetime.now().strftime("%H:%M")
    if now == "23:59":
        today = datetime.date.today()
        if today == deadline:
            await next_job()


daily_job.start()

client.run(TOKEN)