import os
import datetime
import asyncio

import discord
from discord.ext import tasks
from natsort import natsorted

from game import Game

RAISED_HAND = "\N{Raised Hand}"
participation_message = None

try:
    with open("TOKEN.txt", mode = "r") as f:
        TOKEN = f.read()
except:
    print("bot のトークンを TOKEN.txt に書き込んでください")
    exit()

try:
    with open("home_channel_id.txt", mode = "r") as f:
        HOME_CHANNEL_ID = int(f.read())
except:
    HOME_CHANNEL_ID = None


client = discord.Client(intents=discord.Intents.all())


@client.event
async def on_ready():
    global game
    game = Game(client, HOME_CHANNEL_ID)
    try:
        game.load()
        if game.is_ongoing:
            print("Latest game loaded")
            if game.current_turn == game.number_of_participants - 1:
                await game.next_job()
    except:
        game.is_accepting = 0
        game.is_ongoing = 0
        print("Latest game did not load")

    daily_job.start()
    print("Successfully activated")


@client.event
async def on_message(message):
    global HOME_CHANNEL_ID, game, participation_message

    game_admin_role = discord.utils.get(message.guild.roles, name="1WGP_admin")
    if game_admin_role is None:
        game_admin_role = await message.guild.create_role(name="1WGP_admin")

    have_admin_permission = message.author.guild_permissions.administrator or game_admin_role in message.author.roles

    if not message.content.startswith("!"):
        return

    elif message.content.startswith("!set_home_channel"):
        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        HOME_CHANNEL_ID = message.channel.id

        with open("home_channel_id.txt", mode = "w") as f:
            f.write(str(HOME_CHANNEL_ID))

        await message.channel.send("このチャンネルを 1WGP のホームチャンネルに設定しました")

    elif HOME_CHANNEL_ID is None:
        await message.channel.send("```\n!set_home_channel\n```でホームチャンネルを設定してください")

    elif message.content.startswith("!give_admin_role"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        for user_mention in message.mentions:
            member = message.guild.get_member(user_mention.id)
            await member.add_roles(game_admin_role)

            await message.channel.send(f"{member.mention} にゲーム管理者のロールを付与しました")

    elif message.content.startswith("!new_game"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            await message.channel.send("現在進行中のゲームがあるようです。新しくゲームを始める場合、 \
                ```\n!cancel_game\n```\nを用いて進行中のゲームを中断してください")
        else:
            participation_message = await message.channel.send(f"参加希望者はこのメッセージに {RAISED_HAND} のリアクションをつけてください")
            await participation_message.add_reaction(RAISED_HAND)
            game = Game(client, HOME_CHANNEL_ID)

    elif message.content.startswith("!confirm"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_accepting:
            participant_mention_list = [participant_i.mention for participant_i in game.participants]
            confirm_message = "以下のメンバーでゲームを開始します\n" + "\n".join(participant_mention_list)
            await message.channel.send(confirm_message)

            game.start()
            game.save()

            for individual_channel in game.individual_channels:
                await individual_channel.send(f"{game.deadline} 23:59 までにお題を送信してください")
        else:
            await message.channel.send("```\n!new_game\n```\nを用いてゲーム参加者を募集してください")

    elif message.content.startswith("!cancel_game"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        game.reset()

        await message.channel.send("現在進行中のゲームを中断しました")

    elif message.content.startswith("!skip_turn"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            await game.next_job()

    elif message.content.startswith("!show_subjects"):
        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            subjects = []
            for turn in range(0, game.current_turn, 2):
                for game_index in range(game.number_of_participants):
                    target_path = os.path.join(game.start_date, str(turn), str(game_index))
                    file_name = natsorted(os.listdir(target_path))[-1]
                    with open(os.path.join(target_path, file_name), mode = "r") as f:
                        subjects.append(f"{turn} {game_index} ```{f.read()}```")
            
            await message.channel.send("\n".join(subjects))

    elif message.content.startswith("!show_turn"):
        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            await message.channel.send(f"{game.current_turn}")

    elif message.content.startswith("!add_participants"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_accepting:
            for member in message.mentions:
                # TODO: あとで on_reaction_add とまとめる。複数回追加される可能性あり
                user = client.get_user(member.id)
                category = message.channel.category
                channel_name = user.name

                game.append_participant(user)

                # 目的のチャンネルがすでに作られているとき
                channel_exists = 0
                for channel_i in category.text_channels:
                    if channel_name == channel_i.name:
                        game.append_channel(channel_i)
                        channel_exists = 1
                        break

                if channel_exists:
                    continue

                # プライベートチャンネルに設定するための dict
                permission = {
                    message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    user: discord.PermissionOverwrite(read_messages=True),
                    client.user: discord.PermissionOverwrite(read_messages=True)
                }

                channel = await category.create_text_channel(name=channel_name, overwrites=permission)

                game.append_channel(channel)

                await channel.send("このチャンネルで画像、テキストの送受信をしてください")

    elif message.content.startswith("!remind"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            sending_object = "お題" if game.current_turn == 0 else "絵" if game.current_turn % 2 else "絵の説明"
            for user_i in game.participants:
                if user_i in game.completed_users:
                    continue
                for channel_i in game.individual_channels:
                    if channel_i.name == user_i.name:
                        await channel_i.send(f"現在提出が確認されていません。{game.deadline} 23:59 までに{sending_object}を送信してください。")
                        break

    elif message.content.startswith("!next"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not have_admin_permission:
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            game.is_waiting_for_next = 0

    elif message.content.startswith("!help"):
        help_images = [
            discord.File(os.path.join("help", "set_home_channel.png")),
            discord.File(os.path.join("help", "new_game.png")),
            discord.File(os.path.join("help", "confirm.png")),
            discord.File(os.path.join("help", "send_subject.png")),
            discord.File(os.path.join("help", "send_picture.png")),
        ]

        with open(os.path.join("help", "message.txt"), mode = "r") as f:
            help_message = f.read()

        await message.channel.send(help_message, files=help_images)

    elif message.content.startswith("!progress"):
        if game.is_ongoing:
            await message.channel.send(
                f"現在の提出状況\n{len(game.completed_users)} / {game.number_of_participants}")
        else:
            await message.channel.send("現在進行中のゲームはないようです")

    elif message.content.startswith("!send_subject"):
        if message.channel not in game.individual_channels:
            return

        if message.channel.name != message.author.name and not have_admin_permission:
            return

        if not game.is_ongoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if game.current_turn % 2 == 1:
            await message.channel.send("現在、絵を送信するフェーズです。\n```\n!send_picture\n```\nを用いて画像を送信してください")
            return

        for user_i in game.participants:
            if user_i.name == message.channel.name:
                author = user_i
                break
        user_index = game.passing_table[game.current_turn].index(author)
        target_path = os.path.join(game.start_date, str(game.current_turn), str(user_index))
        files = os.listdir(target_path)
        accepted_subject = message.content.replace("!send_subject", "")
        with open(os.path.join(target_path, f"{len(files)}_subject.txt"), mode = "w") as f:
            f.write(accepted_subject)

        await message.channel.send(f"以下の文章を受理しました\n```\n{accepted_subject}\n```")

        game.completed_users.add(author)
        if len(game.completed_users) == game.number_of_participants and not game.is_in_phase_transition:
            game.is_in_phase_transition = 1

            await asyncio.sleep(300)
            await game.next_job()
            
            game.is_in_phase_transition = 0

    elif message.content.startswith('!send_picture'):
        if message.channel not in game.individual_channels:
            return

        if message.channel.name != message.author.name and not have_admin_permission:
            return

        if not game.is_ongoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if game.current_turn % 2 == 0:
            await message.channel.send("現在、お題もしくは絵の説明を送信するフェーズです。\n```\n!send_subject\n```\nを用いて文章を送信してください")
            return

        for user_i in game.participants:
            if user_i.name == message.channel.name:
                author = user_i
                break
        user_index = game.passing_table[game.current_turn].index(author)
        target_path = os.path.join(game.start_date, str(game.current_turn), str(user_index))

        attachment = message.attachments[0]
        files = os.listdir(target_path)
        file_name = os.path.join(target_path, f"{len(files)}_{attachment.filename}")
        await attachment.save(file_name)

        await message.channel.send(f"以下の画像を受理しました", file=discord.File(file_name))

        game.completed_users.add(author.id)
        if len(game.completed_users) == game.number_of_participants and not game.is_in_phase_transition:
            game.is_in_phase_transition = 1

            await asyncio.sleep(300)
            await game.next_job()
            
            game.is_in_phase_transition = 0

    else:
        await message.channel.send("定義されていないコマンドです")


@client.event
async def on_reaction_add(reaction, user):
    global game, participation_message

    message = reaction.message
    category = message.channel.category
    channel_name = user.name

    if participation_message is None:
        return

    if message != participation_message or user == client.user:
        return

    game.append_participant(user)

    # 目的のチャンネルがすでに作られているとき
    for channel_i in category.text_channels:
        if channel_name == channel_i.name:
            game.append_channel(channel_i)
            return

    # プライベートチャンネルに設定するための dict
    permission = {
        message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True),
        client.user: discord.PermissionOverwrite(read_messages=True)
    }

    channel = await category.create_text_channel(name=channel_name, overwrites=permission)

    game.append_channel(channel)

    await channel.send("このチャンネルで画像、テキストの送受信をしてください")


@client.event
async def on_reaction_remove(reaction, user):
    global game, participation_message

    message = reaction.message

    if participation_message is None:
        return

    if message != participation_message or user == client.user:
        return

    game.remove_participant(user)
    for channel_i in message.channel.category.text_channels:
        if user.name == channel_i.name:
            game.remove_channel(channel_i)
            return


@tasks.loop(seconds=60)
async def daily_job():
    global game

    if not game.is_ongoing:
        return

    now = datetime.datetime.now().strftime("%H:%M")
    today = str(datetime.date.today())

    if game.is_in_phase_transition:
        return

    if today == game.deadline and now == "23:59":
        await game.next_job()
    elif today > game.deadline:
        await game.next_job()


client.run(TOKEN)
