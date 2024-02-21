import os
import shutil
import datetime
import random

import discord
from discord.ext import tasks


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

        self.deadline = str(datetime.date.today() + datetime.timedelta(days=7))
        self.is_accepting = 0
        self.is_ongoing = 1
        self.current_turn = 0
        self.completed_users = set()

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
        global HOHME_CHANNEL_ID
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

                    if turn % 2 == 0:
                        with open(os.path.join(target_path, "subject.txt"), mode = "r") as f:
                            subject = f.read()
                        await thread.send(f"{creator.mention}\n```\n{subject}\n```")

                    else:
                        file_name = os.listdir(target_path)[0]
                        await thread.send(f"{creator.mention}", file=discord.File(os.path.join(target_path, file_name)))

            self.reset()

            return

        # send_subject が全員分揃ったとき
        if self.current_turn % 2 == 0:
            for game_index in range(self.number_of_participants):
                next_user = self.passing_table[self.current_turn+1][game_index]
                for destination_channel in self.individual_channels:
                    if destination_channel.name == next_user.name:
                        break

                target_path = os.path.join(self.start_date, str(self.current_turn), str(game_index))
                with open(os.path.join(target_path, "subject.txt"), mode = "r") as f:
                    subject = f.read()

                await destination_channel.send(f"次のお題について絵を描いてください\n```\n{subject}\n```")

            self.update_deadline(datetime.timedelta(days=7))

        else:
            for game_index in range(self.number_of_participants):
                next_user = self.passing_table[self.current_turn+1][game_index]
                for destination_channel in self.individual_channels:
                    if destination_channel.name == next_user.name:
                        break

                target_path = os.path.join(self.start_date, str(self.current_turn), str(game_index))
                file_name = os.listdir(target_path)[0]
                await destination_channel.send(f"次の絵の説明をしてください", file=discord.File(os.path.join(target_path, file_name)))

            self.update_deadline(datetime.timedelta(days=1))

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


async def next_job():
    global HOME_CHANNEL_ID, game


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
        if game.is_ongoing:
            await message.channel.send("現在進行中のゲームがあるようです。新しくゲームを始める場合、 \
                ```\n!cancel_game\n```\nを用いて進行中のゲームを中断してください")
        else:
            participation_message = await message.channel.send(f"参加希望者はこのメッセージに {RAISED_HAND} のリアクションをつけてください")
            await participation_message.add_reaction(RAISED_HAND)
            game = Game()

    elif message.content.startswith("!confirm"):
        if game.is_accepting:
            participant_mention_list = [participant_i.mention for participant_i in game.participants]
            confirm_message = "以下のメンバーでゲームを開始します\n" + "\n".join(participant_mention_list)
            await message.channel.send(confirm_message)

            game.start()
            game.save()

        else:
            await message.channel.send("```\n!new_game\n```\nを用いてゲーム参加者を募集してください")

    elif message.content.startswith("!cancel_game"):
        game.reset()

        await message.channel.send("現在進行中のゲームを中断しました")

    elif message.content.startswith("!send_subject"):
        if message.channel not in game.individual_channels:
            return

        if not game.is_ongoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if game.current_turn % 2 == 1:
            await message.channel.send("現在、絵を送信するフェーズです。\n```\n!send_picture\n```\nを用いて画像を送信してください")
            return

        user_index = game.passing_table[game.current_turn].index(message.author)
        target_path = os.path.join(game.start_date, str(game.current_turn), str(user_index))
        with open(os.path.join(target_path, "subject.txt"), mode = "w") as f:
            f.write(message.content.replace("!send_subject", ""))

        game.completed_users.add(message.author.id)
        if len(game.completed_users) == game.number_of_participants:
            await game.next_job()

    elif message.content.startswith('!send_picture'):
        if message.channel not in game.individual_channels:
            return

        if not game.is_ongoing:
            await message.channel.send("現在進行中のゲームがありません")
            return

        if game.current_turn % 2 == 0:
            await message.channel.send("現在、お題もしくは絵の説明を送信するフェーズです。\n```\n!send_subject\n```\nを用いて文章を送信してください")
            return

        user_index = game.passing_table[game.current_turn].index(message.author)
        target_path = os.path.join(game.start_date, str(game.current_turn), str(user_index))

        attachment = message.attachments[0]
        file_name = os.path.join(target_path, attachment.filename)
        await attachment.save(file_name)

        game.completed_users.add(message.author.id)
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
        today = datetime.date.today()
        if today == game.deadline:
            await game.next_job()


client.run(TOKEN)