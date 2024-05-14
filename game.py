import os
import shutil
import datetime
import random
import asyncio

import discord
from natsort import natsorted

class Game:
    def __init__(self, client, HOME_CHANNEL_ID):
        self.client = client
        self.HOME_CHANNEL_ID = HOME_CHANNEL_ID
        self.participants = []
        self.individual_channels = []
        self.is_accepting = 1
        self.is_ongoing = 0
        self.is_in_phase_transition = 0

    def reset(self):
        self.participants = []
        self.individual_channels = []
        self.is_accepting = 0
        self.is_ongoing = 0
        self.is_in_phase_transition = 0

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
        self.is_in_phase_transition = 0
        self.is_waiting_for_next = 1
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
        self.participants = [self.client.get_user(user_id) for user_id in participants_id]
        self.number_of_participants = len(self.participants)
        passing_table_id = []
        with open(os.path.join("latest_game", "passing_table.txt"), mode = "r") as f:
            for turn in range(self.number_of_participants):
                passing_table_id.append(list(map(int, f.readline().split())))
        self.passing_table = []
        for turn in range(self.number_of_participants):
            self.passing_table.append([self.client.get_user(user_id) for user_id in passing_table_id[turn]])
        with open(os.path.join("latest_game", "individual_channels.txt"), mode = "r") as f:
            individual_channels_id = list(map(int, f.read().split()))
        self.individual_channels = [self.client.get_channel(channel_id) for channel_id in individual_channels_id]
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
            skipped_user = self.client.get_user(skipped_user_id)
            self.unsubmitted_tasks[(turn, game_index)] = skipped_user
        self.is_in_phase_transition = 0
        self.is_waiting_for_next = 1

    def append_participant(self, user):
        if user not in self.participants:
            self.participants.append(user)

    def remove_participant(self, user):
        if user in self.participants:
            self.participants.remove(user)

    def append_channel(self, channel):
        if channel not in self.individual_channels:
            self.individual_channels.append(channel)

    def remove_channel(self, channel):
        if channel in self.individual_channels:
            self.individual_channels.remove(channel)

    def update_deadline(self, time_difference):
        self.deadline = str(datetime.date.today() + time_difference)

    async def next_job(self):
        if self.current_turn == self.number_of_participants - 1:
            home_channel = self.client.get_channel(self.HOME_CHANNEL_ID)
            await home_channel.send("ゲームが終了しました。\n```\n!next\n```を用いて結果の表示を行ってください")

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

                    while self.is_waiting_for_next:
                        await asyncio.sleep(1)

                    if (turn, game_index) in self.unsubmitted_tasks:
                        skipped_user = self.unsubmitted_tasks[(turn, game_index)]
                        await thread.send(f"{skipped_user.mention} skipped")

                    if turn % 2 == 0:
                        with open(os.path.join(target_path, file_name), mode = "r") as f:
                            subject = f.read()
                        await thread.send(f"{creator.mention}\n```\n{subject}\n```")

                    else:
                        await thread.send(f"{creator.mention}", file=discord.File(os.path.join(target_path, file_name)))
                    
                    self.is_waiting_for_next = 1

            await home_channel.send("全ての結果表示が終了しました")
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
                        turn = self.current_turn + turn_difference
                        if turn < self.number_of_participants:
                            alternative_user = self.passing_table[turn][game_index]
                            turn_extra = self.current_turn
                            try:
                                game_index_extra = self.passing_table[turn_extra].index(alternative_user)
                                target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                                file_name = natsorted(os.listdir(target_path))[-1]
                                with open(os.path.join(target_path, file_name), mode = "r") as f:
                                    subject = f.read()
                                break
                            except:
                                pass

                        turn = self.current_turn - turn_difference
                        if 0 <= turn < self.number_of_participants:
                            alternative_user = self.passing_table[turn][game_index]
                            turn_extra = self.current_turn
                            try:
                                game_index_extra = self.passing_table[turn_extra].index(alternative_user)
                                target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
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
                target_path = os.path.join(self.start_date, str(self.current_turn), str(game_index))
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
                            try:
                                game_index_extra = self.passing_table[turn_extra].index(alternative_user)
                                target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                                file_name = natsorted(os.listdir(target_path))[-1]
                                break
                            except:
                                pass

                        turn = self.current_turn - turn_difference
                        if 0 <= turn < self.number_of_participants:
                            alternative_user = self.passing_table[turn][game_index]
                            turn_extra = self.current_turn
                            try:
                                game_index_extra = self.passing_table[turn_extra].index(alternative_user)
                                target_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                                file_name = natsorted(os.listdir(target_path))[-1]
                                break
                            except:
                                pass

                        turn_difference -= 1

                await destination_channel.send(f"次の絵の説明を {self.deadline} 23:59 までに送信してください", file=discord.File(os.path.join(target_path, file_name)))
                if (self.current_turn, game_index) == (turn_extra, game_index_extra):
                    continue

                self.unsubmitted_tasks[(self.current_turn, game_index)] = self.passing_table[self.current_turn][game_index]
                self.passing_table[self.current_turn][game_index] = self.passing_table[turn_extra][game_index_extra]
                self.save()
                original_path = os.path.join(self.start_date, str(turn_extra), str(game_index_extra))
                target_path = os.path.join(self.start_date, str(self.current_turn), str(game_index))
                file_name = natsorted(os.listdir(original_path))[-1]
                shutil.copy(os.path.join(original_path, file_name), os.path.join(target_path, file_name))

        self.completed_users = set()
        self.current_turn += 1

        self.save()
        return
