import random
import discord

import discord.ext
import discord.ext.commands


class Game:
    # liste des joueurs, des rôles, des votes, et des morts
    def __init__(self, player_list: list['Player'], server: discord.Guild):
        # liste des joueurs, des rôles,des votes, et des morts
        self.player_list = player_list
        self.spe_roles = ["president", "cupidon", "hunter", "witch", "stealer"]
        self.vote_list = []
        self.killed_list = {}

        self.roles = self.get_game_roles(server)

        # nombre de tours
        self.round = 0

        # serveur
        self.server = server
        self.channels = server.channels
        self.night_day = None

        self.thread = None

        for channel in self.channels:
            if channel.name == "village":
                self.peasant_channel = channel
            if channel.name == "werewolf":
                self.werewolf_channel = channel
            if channel.name == "specials":
                self.specials_channel = channel

        assert all(
            type(channel) is discord.TextChannel
            for channel in (
                self.peasant_channel,
                self.werewolf_channel,
                self.specials_channel,
            )
        )

    def attribute_game_roles(self):
        print("Attributing games roles to player")

        random.shuffle(self.player_list)
        role_spe1 = None
        role_spe2 = None

        while role_spe1 == role_spe2:
            role_spe1 = random.choice(self.spe_roles)
            role_spe2 = random.choice(self.spe_roles)

        self.player_list[0].role = "werewolf"
        self.player_list[1].role = "werewolf"
        self.player_list[2].role = "peasant"
        self.player_list[3].role = "peasant"
        self.player_list[4].role = "peasant"
        self.player_list[5].role = role_spe1
        self.player_list[6].role = role_spe2

    def get_game_roles(self, guild: discord.Guild):
        roles = [
            role
            for role in guild.roles
            if role.name in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        ]

        print("Keeping roles:")
        for prnt_role in roles:
            print(prnt_role.name, end=", ")
        print("")  # Newline after the printed roles

        random.shuffle(roles)
        return roles

    async def assign_roles(self):
        print("Attributing discord roles to user and channels")
        werewolf_channel = self.werewolf_channel
        specials_channel = self.specials_channel

        roles = self.roles
        print(roles)

        for index, player in enumerate(self.player_list):
            r = roles[index]
            try:
                if player.role == "werewolf":
                    await player.discord.add_roles(r)
                    overwrite = discord.PermissionOverwrite()
                    overwrite.read_message_history = False
                    await werewolf_channel.set_permissions(r, overwrite=overwrite)

                if player.role in [
                    "president",
                    "cupidon",
                    "hunter",
                    "witch",
                    "stealer",
                ]:
                    await player.discord.add_roles(r)
                    overwrite = discord.PermissionOverwrite()
                    overwrite.read_message_history = False
                    await specials_channel.set_permissions(r, overwrite=overwrite)
                else:
                    await player.discord.add_roles(r)
            except Exception as error:
                print(f"Can't assign role {r} to {player.discord.name} : {error}")
                raise error

    async def reset(self):
        print("Deleting roles on users")
        overwrite = discord.PermissionOverwrite()
        overwrite.view_channel = False

        roles = self.roles

        for role in roles:
            await self.werewolf_channel.set_permissions(role, overwrite=overwrite)
            await self.specials_channel.set_permissions(role, overwrite=overwrite)

        for user in self.player_list:
            for role in roles:
                try:
                    await user.discord.remove_roles(role)
                except Exception as error:
                    print(f"Couldn't remove {role} from {user.discord.name} : {error}")

    async def transfer_response(self, r):
        global response
        response = r

    async def await_for_response(self):
        import asyncio

        global response
        while True:
            await asyncio.sleep(1)
            try:
                if response:
                    break
            except Exception:
                pass

    async def start(self, ctx: discord.ext.commands.Context):
        import asyncio

        self.thread = asyncio.create_task(self.game(ctx))
        self.thread.cancel()

    def terminate_game(self):
        thread  = self.thread
        
        
    async def game(self, ctx: discord.ext.commands.Context):
        import asyncio
        try:
            while True:
                self.kill_dict = {}
                self.night_day = "night"
                if await self.night(ctx) is False:
                    break

                self.kill_dict = {}
                self.night_day = "day"
                if await self.day(ctx) is False:
                    break
        except asyncio.CancelledError:
            print("Stopped game...")

    async def night(self, ctx: discord.ext.commands.Context):
        import time
        import asyncio

        global response

        await self.peasant_channel.send("------------------------------------")

        await ctx.send("The village is now asleep.")
        time.sleep(2)
        for player in self.player_list:
            if player.state is True:
                player.state = 0

                if player.role == "werewolf":
                    await self.werewolf_channel.send(
                        f"{player.discord.mention} Choose who to kill with !kill player_name"
                    )
                    try:
                        await asyncio.wait_for(self.await_for_response(), 60)
                        response = None
                    except TimeoutError:
                        await self.werewolf_channel.send(
                            f"{player.discord.mention} your vote is considered blank."
                        )

                elif player.role == "cupidon" and self.round == 0:
                    await self.specials_channel.send(
                        f"{player.discord.mention} Choose the two lovers with !enamorate lover1 lover2"
                    )
                    try:
                        await asyncio.wait_for(self.await_for_response(), 60)
                        lover1_, lover2_ = response
                        try:
                            lover1 = self.get_element_by_attribute(
                                self.player_list, "name", lover1_
                            )[0]
                            lover1.enamored = True
                            lover2 = self.get_element_by_attribute(
                                self.player_list, "name", lover2_
                            )[0]
                            lover2.enamored = True

                            await lover1.discord.send(
                                f"Congratulations, you are in love with {lover2.name}"
                            )
                            await lover2.discord.send(
                                f"Congratulations, you are in love with {lover1.name}"
                            )
                        except Exception:
                            await self.peasant_channel.send(
                                f"Cupidon was tired due to its nightshift, and made ghost fall in love : {lover1_} and {lover2_}"
                            )
                        response = None
                    except TimeoutError:
                        await self.specials_channel.send(
                            f"{player.discord.mention} Your absence of response has caused the love to disappear. Shame on you..."
                        )
                elif player.role == "stealer":
                    await self.specials_channel.send(
                        f"{player.discord.mention} You must exchange your role with someone else with !steal player_name"
                    )
                    try:
                        await asyncio.wait_for(self.await_for_response(), 60)
                        stealed = response
                        try:
                            print(stealed)
                            stealed2 = self.get_element_by_attribute(
                                self.player_list, "name", stealed
                            )[0]
                        except Exception:
                            await self.specials_channel.send(
                                "No one has this name. But I am nice, and I will exchange your role with a random person."
                            )
                            stealed2 = random.choice(self.player_list)
                        player.role = stealed2.role
                        stealed2.role = "stealer"
                        response = None
                    except TimeoutError:
                        await self.specials_channel.send(
                            f"{player.discord.mention} Your chosen one has managed to get away."
                        )
                player.state = True
        for dead in self.kill_dict:
            if self.kill_dict[dead] == "by the wolves.":
                if (
                    self.get_element_by_attribute(self.player_list, "role", "witch")
                    != []
                ):
                    witch = self.get_element_by_attribute(
                        self.player_list, "role", "witch"
                    )[0]
                    witch.state = 0
                    witch = self.get_element_by_attribute(
                        self.player_list, "role", "witch"
                    )[0]
                    await self.specials_channel.send(
                        f"{witch.discord.mention} {dead.name} has been killed by the wolves. You have two choice: save the killed player with !save player_name or kill a person with !poison player_name, or you can do nothing."
                    )
                    try:
                        await asyncio.wait_for(self.await_for_response(), 60)
                        choice, target = response
                        if choice == "save":
                            del self.kill_dict[dead]
                        else:
                            # un IF SUR 5 LIGNES POUR UNE CONDITION?!
                            if (
                                self.get_element_by_attribute(
                                    self.player_list, "name", target
                                )
                                != []
                            ):
                                self.eliminate(target, "by the witch.")
                    except TimeoutError:
                        await self.specials_channel.send(
                            f"{player.discord.mention} You were too tired and did nothing."
                        )
        rep = self.end_vote()
        if rep is False:
            await ctx.send(
                f"The Werewolves were definitely drunk, and tried to vote for a ghost : {rep}"
            )
        elif rep == None:
            await ctx.send(f"The werewolves couldn't come to an agreement, so I guess you're safe for now..")
        else:
            for killed in self.kill_dict.keys():
                await ctx.send(f"{killed} was eliminated{self.kill_dict[killed]}")
        await ctx.send("It's the end of the night.")
        self.round += 1

        werewolves = self.get_element_by_attribute(self.player_list, "role", "werewolf")
        other = self.get_element_by_attribute(
            self.player_list, "role", "werewolf", None, True
        )

        werewolves_count = len(werewolves)
        other_count = 0
        for w in werewolves:
            if w.state is True:
                werewolves_count += 1
        for o in other:
            if o.state is True:
                other_count += 1
        if werewolves_count == 0:
            await self.peasant_channel.send(
                "@everyone The game is finished, and the peasants winned :"
            )
            for o in other:
                await self.peasant_channel.send(o.name)
            return False
        elif werewolves_count >= other_count:
            await self.peasant_channel.send(
                "@everyone The game is finished, and the werewolves winned :"
            )
            for w in werewolves:
                await self.peasant_channel.send(w.name)
            return False
        return True

    async def day(self, ctx: discord.ext.commands.Context):
        import asyncio

        await self.peasant_channel.send("------------------------------------")

        await self.peasant_channel.send(
            "The village is now awake. You can now proceed to the vote."
        )

        president = self.get_element_by_attribute(self.player_list, "role", "president")
        if president != []:
            president = president[0].name
            await self.peasant_channel.send(
                f"You have 1 minute to vote with the command !vote player_name. The president's vote counts for 2, wich is {president}"
            )

        else:
            await self.peasant_channel.send(
                "You have 1 minute to vote with the command !vote player_name."
            )

        await asyncio.sleep(60)
        await self.peasant_channel.send("The vote is now finished.")
        self.end_vote(reason="by the community.")
        for dead in self.kill_dict.keys():
            await self.peasant_channel.send(f"{dead} was killed {self.kill_dict[dead]}")

    def vote(self, vote):
        self.vote_list.append(vote)

    def eliminate(self, voted, reason=None):
        for player in self.player_list:
            if player.name == voted and player.state is True:
                if player.enamored is True:
                    for player in self.get_element_by_attribute(
                        self.player_list, "enamored", True
                    ):
                        player.kill()
                        self.kill_dict[player.name] = "because he was in mad love."

                elif player.role == "hunter":
                    self.eliminate(player.kill(self.specials_channel), "by revenge.")

                elif reason:
                    player.kill()
                    self.kill_dict[player.name] = reason

                else:
                    player.kill()
                    self.kill_dict[player.name] = "by the wolves."
                return voted

        return False

    def end_vote(self, reason=None):
        votes = {}
        if self.vote_list == []:
            return None
        for player in self.vote_list:
            try:
                votes[player] += 1
            except (
                KeyError
            ):  # Si le joueur n'a pas encore reçu de vote, alors son 'compte' est crée
                votes[player] = 1
        max_value = max(dict.items())
        for player in self.vote_list:
            if dict[player] == max_value:
                break
        self.vote_list = []
        return self.eliminate(player, reason)

    def get_element_by_attribute(
        self, list, attribute, match, output_attr=None, inversed=False
    ):
        output = []
        if inversed is False:
            for element in list:
                if getattr(element, attribute) == match:
                    if output_attr:
                        output.append(getattr(element, output_attr))
                    else:
                        output.append(element)
            return output
        else:
            for element in list:
                if getattr(element, attribute) != match:
                    if output_attr:
                        output.append(getattr(element, output_attr))
                    else:
                        output.append(element)
            return output


class Player:
    def __init__(self, name, discord: discord.User | discord.Member):
        self.name = name
        self.discord = discord
        self.state = True
        self.role: str | None = None
        self.enamored = False

    async def kill(self, specials_channel: discord.TextChannel):
        import asyncio

        assert type(specials_channel) is discord.TextChannel
        if self.state is not False:
            self.state = False
            if self.role == "hunter":
                self.state = 0
                await specials_channel.send(
                    "Because of your role, you can take your revenge with !hunt player_name"
                )
                await asyncio.wait_for(self.await_for_response(), 60)
                hunted = response
                response = None
                return hunted

    async def transfer_response(self, r):
        global response
        response = r

    async def await_for_response(self):
        import asyncio

        global response
        while True:
            await asyncio.sleep(1)
            try:
                if response:
                    break
            except Exception:
                pass
