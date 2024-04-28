import os
import shutil
import datetime
import random

import discord
from discord.ext import tasks
from natsort import natsorted


class Game:
    def __init__(self):
        self.participants = []
        self.individual_channels = []
        self.is_accepting = 1
        self.is_ongoing = 0

    def reset(self):
        self.participants = []
        self.individual_channels = []
        self.is_accepting = 0
        self.is_ongoing = 0

        try:
            shutil.rmtree("latest_game")
        except:
            pass
        os.mkdir("latest_game")

    def start(self):
        self.participants.sort(key = lambda user: user.name)
        self.individual_channels.sort(key = lambda channel: channel.name)

        self.number_of_participants = len(self.participants)
        start_date = str(datetime.datetime.now().replace(microsecond=0))
        self.start_date = start_date.replace(" ", "_").replace(":", "-")

        self.passing_table = [[] for i in range(self.number_of_participants)]
        for turn in range(self.number_of_participants):
            for user_index in range(self.number_of_participants):
                os.makedirs(f"{self.start_date}/{turn}/{user_index}")
                user_tmp = self.participants[(turn+user_index)%self.number_of_participants]
                self.passing_table[turn].append(user_tmp)
        random.shuffle(self.passing_table)

        self.deadline = str(datetime.date.today() + datetime.timedelta(days=1))
        self.is_accepting = 0
        self.is_ongoing = 1
        self.current_turn = 0
        self.completed_users = set()
        self.unsubmitted_tasks = dict()

    def save(self):
        try:
            os.mkdir("latest_game")
        except:
            pass

        with open(os.path.join("latest_game", "ongoing.txt"), mode = "w") as f:
            f.write(str(self.is_ongoing))
        with open(os.path.join("latest_game", "start_date.txt"), mode = "w") as f:
            f.write(self.start_date)
        with open(os.path.join("latest_game", "deadline.txt"), mode = "w") as f:
            f.write(self.deadline)
        with open(os.path.join("latest_game", "current_turn.txt"), mode = "w") as f:
            f.write(str(self.current_turn))
        with open(os.path.join("latest_game", "participants.txt"), mode = "w") as f:
            f.write(" ".join([str(user.id) for user in self.participants]))
        with open(os.path.join("latest_game", "passing_table.txt"), mode = "w") as f:
            for turn in range(self.number_of_participants):
                f.write(" ".join([str(user.id) for user in self.passing_table[turn]]) + "\n")
        with open(os.path.join("latest_game", "individual_channels.txt"), mode = "w") as f:
            f.write(" ".join([str(channel.id) for channel in self.individual_channels]))
        with open(os.path.join("latest_game", "unsubmitted_tasks.txt"), mode = "w") as f:
            for turn, game_index in self.unsubmitted_tasks.keys():
                skipped_user = self.unsubmitted_tasks[(turn, game_index)]
                f.write(f"{turn} {game_index} {skipped_user.id}\n")

    def load(self):
        with open(os.path.join("latest_game", "ongoing.txt"), mode = "r") as f:
            self.is_ongoing = int(f.read())
        with open(os.path.join("latest_game", "start_date.txt"), mode = "r") as f:
            self.start_date = f.read()
        with open(os.path.join("latest_game", "deadline.txt"), mode = "r") as f:
            self.deadline = f.read()
        with open(os.path.join("latest_game", "current_turn.txt"), mode = "r") as f:
            self.current_turn = int(f.read())
        with open(os.path.join("latest_game", "participants.txt"), mode = "r") as f:
            participants_id = list(map(int, f.read().split()))
        self.participants = [client.get_user(user_id) for user_id in participants_id]
        self.number_of_participants = len(self.participants)
        passing_table_id = []
        with open(os.path.join("latest_game", "passing_table.txt"), mode = "r") as f:
            for turn in range(self.number_of_participants):
                passing_table_id.append(list(map(int, f.readline().split())))
        self.passing_table = []
        for turn in range(self.number_of_participants):
            self.passing_table.append([client.get_user(user_id) for user_id in passing_table_id[turn]])
        with open(os.path.join("latest_game", "individual_channels.txt"), mode = "r") as f:
            individual_channels_id = list(map(int, f.read().split()))
        self.individual_channels = [client.get_channel(channel_id) for channel_id in individual_channels_id]
        self.completed_users = set()
        for user_index in range(self.number_of_participants):
            target_path = os.path.join(self.start_date, str(self.current_turn), str(user_index))
            if len(os.listdir(target_path)) > 0:
                self.completed_users.add(self.passing_table[self.current_turn][user_index])
        self.unsubmitted_tasks = dict()
        with open(os.path.join("latest_game", "unsubmitted_tasks.txt"), mode = "r") as f:
            unsubmitted_tasks_tmp = f.readlines()
        for task in unsubmitted_tasks_tmp:
            turn, game_index, skipped_user_id = map(int, task.split())
            skipped_user = client.get_user(skipped_user_id)
            self.unsubmitted_tasks[(turn, game_index)] = skipped_user

    def append_participant(self, user):
        self.participants.append(user)

    def remove_participant(self, user):
        self.participants.remove(user)

    def append_channel(self, channel):
        self.individual_channels.append(channel)

    def remove_channel(self, channel):
        self.individual_channels.remove(channel)

    def update_deadline(self, time_difference):
        self.deadline = str(datetime.date.today() + time_difference)

    async def next_job(self):
        if self.current_turn == self.number_of_participants - 1:
            home_channel = client.get_channel(HOME_CHANNEL_ID)
            await home_channel.send("ゲームが終了しました")

            for game_index in range(self.number_of_participants):
                first_participant = self.passing_table[0][game_index]
                message = await home_channel.send(f"{first_participant.name} のお題")
                thread = await message.create_thread(name = f"{first_participant.name} のお題")

                for turn in range(self.number_of_participants):
                    target_path = os.path.join(self.start_date, str(turn), str(game_index))
                    creator = self.passing_table[turn][game_index]
                    try:
                        file_name = natsorted(os.listdir(target_path))[-1]
                    except:
                        await thread.send(f"{creator.mention} skipped")
                        continue

                    if (turn, game_index) in self.unsubmitted_tasks:
                        skipped_user = self.unsubmitted_tasks[(turn, game_index)]
                        await thread.send(f"{skipped_user.mention} skipped")

                    if turn % 2 == 0:
                        with open(os.path.join(target_path, file_name), mode = "r") as f:
                            subject = f.read()
                        await thread.send(f"{creator.mention}\n```\n{subject}\n```")

                    else:
                        await thread.send(f"{creator.mention}", file=discord.File(os.path.join(target_path, file_name)))

            self.reset()
            return

        game_indexes = [i for i in range(self.number_of_participants)]
        random.shuffle(game_indexes)
        game_indexes *= self.number_of_participants # 未提出があまりに多いとき対策

        # send_subject が全員分揃ったとき
        if self.current_turn % 2 == 0:
            self.update_deadline(datetime.timedelta(days=7))

            for game_index in range(self.number_of_participants):
                next_user = self.passing_table[self.current_turn+1][game_index]
                for destination_channel in self.individual_channels:
                    if destination_channel.name == next_user.name:
                        break

                # まず後ろにさかのぼる
                turn_extra = self.current_turn
                game_index_extra = game_index
                subject = ""
                while turn_extra >= 0:
                    target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                    try:
                        file_name = natsorted(os.listdir(target_path))[-1]
                        with open(os.path.join(target_path, file_name), mode = "r") as f:
                            subject = f.read()
                        break
                    except:
                        turn_extra -= 2

                # それでも無いときは他のゲームから持ってくる
                if subject == "":
                    turn_difference = self.number_of_participants - 1
                    while turn_difference > 0:
                        turn_extra = self.current_turn + turn_difference
                        if turn_extra < self.number_of_participants:
                            alternative_user = self.passing_table[turn_extra][game_index]
                            game_index_extra = self.passing_table[self.current_turn].index(alternative_user)
                            target_path = os.path.join(self.start_date, str(self.current_turn), str(game_index_extra))
                            try:
                                file_name = natsorted(os.listdir(target_path))[-1]
                                with open(os.path.join(target_path, file_name), mode = "r") as f:
                                    subject = f.read()
                                break
                            except:
                                pass

                        turn_extra = self.current_turn - turn_difference
                        if turn_extra >= 0:
                            alternative_user = self.passing_table[turn_extra][game_index]
                            game_index_extra = self.passing_table[self.current_turn].index(alternative_user)
                            target_path = os.path.join(self.start_date, str(self.current_turn), str(game_index_extra))
                            try:
                                file_name = natsorted(os.listdir(target_path))[-1]
                                with open(os.path.join(target_path, file_name), mode = "r") as f:
                                    subject = f.read()
                                break
                            except:
                                pass

                        turn_difference -= 1

                await destination_channel.send(f"次のお題について {self.deadline} 23:59 までに絵を描いて送信してください\n```\n{subject}\n```")

                if (self.current_turn, game_index) == (turn_extra, game_index_extra):
                    continue

                self.unsubmitted_tasks[(self.current_turn, game_index)] = self.passing_table[self.current_turn][game_index]
                self.passing_table[self.current_turn][game_index] = self.passing_table[turn_extra][game_index_extra]
                self.save()
                original_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                target_path = os.path.join(self.start_date, str(game.current_turn), str(game_index))
                file_name = natsorted(os.listdir(original_path))[-1]
                shutil.copy(os.path.join(original_path, file_name), os.path.join(target_path, file_name))

        else:
            self.update_deadline(datetime.timedelta(days=1))

            for game_index in range(self.number_of_participants):
                next_user = self.passing_table[self.current_turn+1][game_index]
                for destination_channel in self.individual_channels:
                    if destination_channel.name == next_user.name:
                        break

                turn_extra = self.current_turn
                game_index_extra = game_index
                file_name = ""
                while turn_extra >= 0:
                    target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                    try:
                        file_name = natsorted(os.listdir(target_path))[-1]
                        break
                    except:
                        turn_extra -= 2

                if file_name == "":
                    turn_difference = self.number_of_participants - 1
                    while turn_difference > 0:
                        turn = self.current_turn + turn_difference
                        if turn < self.number_of_participants:
                            alternative_user = self.passing_table[turn][game_index]
                            turn_extra = self.current_turn
                            game_index_extra = self.passing_table[turn_extra].index(alternative_user)
                            target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                            try:
                                file_name = natsorted(os.listdir(target_path))[-1]
                                break
                            except:
                                pass

                        turn = self.current_turn - turn_difference
                        if 0 <= turn < self.number_of_participants:
                            alternative_user = self.passing_table[turn][game_index]
                            turn_extra = self.current_turn
                            game_index_extra = self.passing_table[turn_extra].index(alternative_user)
                            target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                            try:
                                file_name = natsorted(os.listdir(target_path))[-1]
                                break
                            except:
                                pass

                        turn_difference -= 1

                await destination_channel.send(f"次の絵の説明を {self.deadline} 23:59 までに送信してください", file=discord.File(os.path.join(target_path, file_name)))
                print((self.current_turn, game_index),  (turn, game_index_extra), (self.current_turn, game_index) == (turn, game_index_extra))
                if (self.current_turn, game_index) == (turn_extra, game_index_extra):
                    continue

                self.unsubmitted_tasks[(self.current_turn, game_index)] = self.passing_table[self.current_turn][game_index]
                self.passing_table[self.current_turn][game_index] = self.passing_table[turn_extra][game_index_extra]
                self.save()
                original_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                target_path = os.path.join(self.start_date, str(game.current_turn), str(game_index))
                file_name = natsorted(os.listdir(original_path))[-1]
                shutil.copy(os.path.join(original_path, file_name), os.path.join(target_path, file_name))

        self.completed_users = set()
        self.current_turn += 1

        self.save()
        return


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
    game = Game()
    try:
        game.load()
        if game.is_ongoing:
            print("Latest game loaded")
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

    if not message.content.startswith("!"):
        return

    elif message.content.startswith("!set_home_channel"):
        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
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

        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        for user_mention in message.mentions:
            member = message.guild.get_member(user_mention.id)
            await member.add_roles(game_admin_role)

            await message.channel.send(f"{member.mention} にゲーム管理者のロールを付与しました")

    elif message.content.startswith("!new_game"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            await message.channel.send("現在進行中のゲームがあるようです。新しくゲームを始める場合、 \
                ```\n!cancel_game\n```\nを用いて進行中のゲームを中断してください")
        else:
            participation_message = await message.channel.send(f"参加希望者はこのメッセージに {RAISED_HAND} のリアクションをつけてください")
            await participation_message.add_reaction(RAISED_HAND)
            game = Game()

    elif message.content.startswith("!confirm"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
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

        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        game.reset()

        await message.channel.send("現在進行中のゲームを中断しました")

    elif message.content.startswith("!skip_turn"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            await game.next_job()

    elif message.content.startswith("!show_subjects"):
        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
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
        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
            await message.channel.send("このコマンドを実行する権限がありません")
            return

        if game.is_ongoing:
            await message.channel.send(f"{game.current_turn}")

    elif message.content.startswith("!add_participants"):
        if message.channel.id != HOME_CHANNEL_ID:
            return

        if not (message.author.guild_permissions.administrator or game_admin_role in message.author.roles):
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

        if message.channel.name != message.author.name or not message.author.guild_permissions.administrator:
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

        game.completed_users.add(author.id)
        if len(game.completed_users) == game.number_of_participants:
            await game.next_job()

    elif message.content.startswith('!send_picture'):
        if message.channel not in game.individual_channels:
            await message.channel.send("error: This channel is not for gaming")
            return

        if message.channel.name != message.author.name or not message.author.guild_permissions.administrator:
            await message.channel.send("rejected")
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
        if len(game.completed_users) == game.number_of_participants:
            await game.next_job()

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
    now = datetime.datetime.now().strftime("%H:%M")
    if now == "23:59":
        today = str(datetime.date.today())
        if today == game.deadline:
            await game.next_job()


client.run(TOKEN)
