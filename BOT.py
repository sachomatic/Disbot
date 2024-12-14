#! /bin/env python3

import os
import time
import datetime
import logging
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from Werewolf_game import Game, Player

"""
Ceci est une tentative du jeu du loup garou sur un bot discord.
Toutes les fonctions doivent être asynchrones

ctx: command.Context -> contexte discord, dans notre cas, c'est les messages appellant la fonction.
	.send() : envoyer dans le channel où le message a été envoyé
	.guild : le serveur du message
	.author : l'auteur du message

player : dans notre cas, utilisateur
	.send() : envoyer dans les messages privés

"""

# chargement des informations utiles s
response = load_dotenv()
if response:
    TOKEN = os.getenv("DISCORD_TOKEN")
    SERVER = os.getenv("DISCORD_SERVER")
    PERMISSIONS = os.getenv("DISCORD_PERMISSIONS")
else:
    print("TOKEN is not present. Is it adviced to quit")
    if input("Continue anyway? (enter to continue) : ") != "":
        quit()

# buts/permissions (lire les messages,réagir,accéder aux infos des membres,gérer les channels et les rôles )
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
overwrite = discord.PermissionOverwrite()
overwrite.read_messages = False
overwrite.manage_channels = True
overwrite.manage_roles = True

# création du bot/connexion à discord
bot = commands.Bot(command_prefix="!", intents=intents, overwrite=overwrite)

# date de démarrage et infos liés au temps
og_time = time.time()

d = {
    0: "monday",
    1: "tuesdays",
    2: "wednesdays",
    3: "thursdays",
    4: "friday",
    5: "saturday",
    6: "sunday",
}

og_days = d[datetime.datetime.now().weekday()]
og_day_nb = datetime.datetime.now().day
og_hours = datetime.datetime.now().hour
og_minutes = datetime.datetime.now().minute


def get_decimal_numbers(number: float):
    # Obtenir les chiffres décimaux d'un flottant
    number_str = str(number)
    decimal_index = number_str.find(".")
    if decimal_index == -1:
        return 0.0

    return float(number_str[decimal_index:])


@bot.command(name="create_game")
async def create_game(ctx: commands.Context, *args, **kwargs):
    # La fonction pour commencer une partie
    global game_start
    global player_lst
    await ctx.send(
        "@everyone Starting game in 1 minute. Use !start to start now and !join to join the game! There must be at least 4 players to start the game and maximum 10 players"
    )
    game_start = False
    player_lst = []
    # On attends une minute pour que les jouers rejoignent, puis on lance la partie
    for i in range(60):
        await asyncio.sleep(1)
        if game_start:
            return
    await start_game(ctx)


@bot.command(name="start")
async def start_game(ctx: commands.Context, *args, **kwargs):
    import math
    assert ctx.guild is not None
    # Lancer la partie, peut être appelé avant la fin du timer
    global game_start
    global player_lst
    global game
    if player_lst == []:
        await ctx.send("No one has joined, game is canceled.")
        cancel_game()
        return
    elif len(player_lst) < 3:
        await ctx.send("Not enough player joined, game is canceled.")
        return
    if "game" in globals():
        await ctx.send("Game was already started.")
        return
    try:
        start_time = time.time()
        game_start = True

        # Game() est la classe qui gère la partie en cours
        game = Game(player_lst, ctx.guild)

        await ctx.send("Starting game with:", delete_after=5)
        temp = ''.join(player_lst)
        await ctx.send(temp)

        await ctx.send("Preparing game... Please wait while the roles are resetting.")
        try:
            # Les rôles de la partie précédente, si ils existent, sont retirés
            await game.reset()
        except Exception:
            logging.exception("")
            await ctx.send(
                "Error : roles couldn't be resetted, game will continue but might crash"
            )

        # Attribution des permissions pour chaque channel
        game.attribute_game_roles()
        for player in game.player_list:
            await player.discord.send(f"Hello {player.discord.global_name}You are a {player.role}")
        end_time = time.time()
        final_time = end_time - start_time
        minutes = final_time // 60
        seconds = round(final_time % 60)
        await ctx.send(f"Took {int(minutes)}:{math.floor(seconds)} to prepare game.",delete_after=10)
        # attribution des rôles
        await game.assign_roles()
        await game.start(ctx)

    except NameError:
        await ctx.send("Game is not created. Please use !create_game.")
        logging.exception("")
        return
    except KeyError:
        logging.exception("")
        await ctx.send("Not enough players to start game")
    except Exception:
        logging.exception("")
        await ctx.send(
            "An error occured, causing the game to crash. Please restart it."
        )
    finally:
        game = None
        game_start = False
        player_lst = []


async def search_channel(name, server):
    # Chercher dans le serveur une channel particulière
    for channel in server.channels:
        if str(channel.name) == str(name):
            return channel


async def get_roles():
    roles_list = ["1", "2", "3", "4", "5", "6", "7"]
    fn_roles_list = []
    try:
        if game:
            for role in game.server:
                if role.name in roles_list:
                    fn_roles_list.append(role)
            return fn_roles_list
    except Exception:
        return False


# Commandes pour les rôles spéciaux (autre que les villageois)


@bot.command(name="kill")
async def kill(ctx: commands.Context, *args, **kwargs):
    global game
    # on vérifie que la partie est crée
    if not game_start:
        await ctx.send("Game is not created")
        return
    # obtention des noms des loup garou
    player_list = game.get_element_by_attribute(game.player_list, "role", "werewolf")
    try:
        # obtention du joueur qui a lancé la commande et vérification qu'il est loup garou
        player_name = game.get_element_by_attribute(
            player_list, "name", ctx.author.display_name
        )
        # On vérifie que le joueur n'est pas mort
        if player_list[0].state == True and player_name[0] == ctx.author:
            try:
                # obtention du jouer pour lequel le loup garou a voté
                name = args[0]
                await ctx.send(f"Voted for {name}")
            except Exception:
                await ctx.send("Player name missing.")
                return
            # La partie est en suspension en attendant (il y a un timeout) que les loups garou votent
            game.vote(name)
            await game.transfer_response(name)
        else:
            await ctx.send("You are dead or are not a werewolf")
            print(player_list[0].state, player_list[0].role)
    except Exception:
        logging.exception("")


@bot.command(name="enamorate")
async def enamorate(ctx: commands.Context, *args, **kwargs):
    global game
    # on vérifie que la partie est crée
    if not game_start:
        await ctx.send("Game is not created")
        return
    # Obtention du joueur
    player = game.get_element_by_attribute(game.player_list, "role", "cupidon", "name")[
        0
    ]
    # Vérification que le joueur est bien cupidon et n'est pas mort
    if ctx.author.display_name == player.name and player.state == 0:
        try:
            # obtention des deux amoureux
            lover1 = args[0]
            lover2 = args[1]
            # on vérifie que les deux joueurs ne sont pas les mêmes
            if lover1 == lover2:
                await ctx.send("Lovers can't be the same")
                return
        # Si le joueur n'a pas fourni d'arguments, sa réponse est invalidée
        except KeyError:
            await ctx.send("Two lovers must be specified")
            return
        # on envoie la 'requête' à la partie
        await game.transfer_response((lover1, lover2))
    else:
        await ctx.send("You are not cupidon or are dead.")


@bot.command(name="steal")
async def steal(ctx: commands.Context, *args, **kwargs):
    global game
    # on vérifie que la partie est crée
    if not game_start:
        await ctx.send("Game is not created")
        return
    player = game.get_element_by_attribute(game.player_list, "role", "stealer", "name")[
        0
    ]
    # on vérifie que le joueur est vivant et qu'il est voleur
    if ctx.author.display_name == player and player.state == 0:
        try:
            stealed = args[0]
            # on vérifie que le jouer ne se vole pas lui même
            if ctx.author == stealed:
                await ctx.send("You can't steal yourself.")
                return
            else:
                # on transfère les données
                await game.transfer_response(stealed)
        # Si le joueur n'a pas fourni d'arguments, sa réponse est invalidée
        except Exception:
            await ctx.send("No player chosen.")
            return
    else:
        await ctx.send("You are not a stealer or are dead.")


@bot.command("hunt")
async def hunt(ctx: commands.Context, *args, **kwargs):
    global game
    # on vérifie que la partie est crée
    if not game_start:
        await ctx.send("Game is not created")
        return
    player = game.get_element_by_attribute(game.player_list, "role", "hunt")[0]
    # on vérifie que le jouer est vivant et qu'il est chasseur
    if ctx.author.display_name == player.name and player.state == 0:
        try:
            hunted = args[0]
            # on vérifie que le joueur ne se tue pas lui même
            if ctx.author == hunted:
                await ctx.send("You can't shoot yourself.")
                return
            else:
                # on transfère les données
                await game.transfer_response(hunted)
        # Si le joueur n'a pas fourni d'arguments, sa réponse est invalidée
        except Exception:
            await ctx.send("No player chosen.")
            return
    else:
        await ctx.send("You are not a hunter or have not the chance to hunt yet..")


@bot.command(name="save")
async def save(ctx: commands.Context, *args, **kwargs):
    global game
    # on vérifie que la partie est crée
    if not game_start:
        await ctx.send("Game is not created")
        return
    player = game.get_element_by_attribute(game.player_list, "role", "witch")[0]
    # on vérifie que le jouer est une sorcière
    if ctx.author.display_name == player.name and player.state == 0:
        # on transfère les données
        await game.transfer_response(["save", None])
    else:
        await ctx.send("You are not a witch or are dead.")


@bot.command(name="poison")
async def poison(ctx: commands.Context, *args, **kwargs):
    global game
    if not game_start:
        await ctx.send("Game is not created")
        return
    player = game.get_element_by_attribute(game.player_list, "role", "witch", "name")[0]
    # on vérifie que le jouer est une sorcière
    if ctx.author.display_name == player and player.state == 0:
        try:
            target = args[0]
            # on vérifie que le joueur ne se tue pas lui même
            if ctx.author == target:
                await ctx.send("You can't kill yourself.")
                return
            else:
                # on transfère les données
                await game.transfer_response(["kill", target])
        # Si le joueur n'a pas fourni d'arguments, sa réponse est invalidée
        except KeyError:
            await ctx.send("No player chosen.")
            return
    else:
        await ctx.send("You are not a witch or are dead.")


@bot.command(name="vote")
async def vote(ctx: commands.Context, *args, **kwargss):
    global game
    # on vérifie que la partie est crée
    if not game_start:
        await ctx.send("Game is not created")
        return
    user = game.get_element_by_attribute(
        game.player_list, "name", ctx.author.display_name
    )
    # On vérifie que le joueur est vivant et que c'est le jour
    if user.state is True:
        if game.night_day == "day":
            try:
                voted = args[0]
            # Si le joueur n'a pas fourni d'arguments, sa réponse est invalidée
            except IndexError:
                await ctx.send("No player chosen.")
                return
            game.vote(voted)
        else:
            ctx.send("It's not the time to vote yet.")
    else:
        await ctx.send("You're dead, you can't vote")


# commande pour préparer le jeu, à n'éxécuter qu'une fois pour chaque serveur
@bot.command(name="setup")
async def setup(ctx: commands.Context):
    assert ctx.guild is not None
    await ctx.send("Setting up")
    temp = Game(["me"], ctx.guild)
    await ctx.send("Creating channels...")
    ver = False
    for channel in ctx.guild.channels:
        if str(channel) == "werewolf":
            ver = True
    if ver is False:
        await ctx.guild.create_text_channel("werewolf")
    ver = False
    for channel in ctx.guild.channels:
        if str(channel) == "village":
            ver = True
    if ver is False:
        await ctx.guild.create_text_channel("village")
    await ctx.guild.create_text_channel("specials")
    # for i in range(1, 10):
    #     await create_role(ctx, i)
    await ctx.send("done")
    # guild = ctx.guild


@bot.command(name="cancel")
async def cancel_game(ctx: commands.Context):
    global game_start
    game_start = False
    await ctx.send("Game stopped")

@bot.command("stop")
async def stop_game(ctx:commands.Context):
    global game
    if game != None:
        game.terminate_game()
        await ctx.send("Game terminated")
    else:
        await ctx.send("Game isn't launched")


@bot.command("hello")
async def dm_me(ctx: commands.Context, *args, **kwargs):
    print(ctx.author.id)


@bot.command(name="join")
async def join_list(ctx: commands.Context, *args, **kwargs):
    global player_lst
    if len(player_lst) >= 10:
        await ctx.send("Sorry, the game is full, so you can't join.")
        return
    if "game" in globals():
        await ctx.send("Sorry, the game is already started")
        return
    player_lst.append(Player(ctx.author.display_name, ctx.author))
    await ctx.send(f"{ctx.author} just joined the game!")


@bot.command(name="fill")
async def fill_game(ctx: commands.Context, *args, **kwargs):
    global player_lst
    if "game" in globals():
        await ctx.send("Sorry, the game is already started")
        return
    await ctx.send("This function is meant for testing only")
    try:
        fill_number = int(args[0])
    except Exception:
        fill_number = 7
    await ctx.send(f"Joining {fill_number} times")
    for i in range(fill_number):
        player_lst.append(Player(ctx.author.display_name, ctx.author))


@bot.command(name="see_commands")
async def show_commands(ctx: commands.Context, *args, **kwargs):
    """
    Command to see all the commands
    """
    for cmd in bot.commands:
        await ctx.send("Deprecated, use !help")


@bot.command(name="stop_bot")
async def stop_bot(ctx: commands.Context, *args, **kwargs):
    await ctx.send("Stopping...")
    quit()


@bot.command(name="delete_all")
async def delete_all_messages(ctx: commands.Context, *args, **kwargs):
    global cancel
    count = 0
    await ctx.send("DELETING ALL MESSAGE @everyone. Type !cancel to cancel.")
    # try:
    async for message in ctx.channel.history(limit=None):
        time.sleep(0.6)
        if message.content != "DELETING ALL MESSAGE @everyone. Type !cancel to cancel.":
            await message.delete()
        elif count == 1:
            await message.delete()
        else:
            count = 1
        try:
            if cancel:
                cancel = None
                break
        except Exception:
            pass
    await ctx.send("Finished", delete_after=5)
    # except Limi:
    #     await ctx.send("Rate limit reached. Try again later.")


@bot.command(name="test")
async def test(ctx: commands.Context, *args, **kwargs):
    assert ctx.guild is not None
    local_time = time.time() - og_time
    t_hours = local_time / 60 / 60
    tampon = get_decimal_numbers(t_hours)
    hours = int(t_hours)
    t_minutes = tampon * 60
    tampon = get_decimal_numbers(t_minutes)
    minutes = int(t_minutes)
    seconds = int(tampon * 60)
    await ctx.send(
        f"Hello '{ctx.author}'. Running since {og_days} the {og_day_nb}, at {og_hours}h{og_minutes}m, for {hours}:{minutes}:{seconds}."
    )
    await ctx.send(f"Members of {ctx.guild}:")
    for members in ctx.guild.members:
        await ctx.send(f"-{members}")
    await ctx.send("I am on ")


"""@bot.event()
async def on_message(ctx):
	#regarde si le joeur est dans le serveur de jeu
	if ctx.author in members.keys:
		#regarde si le joeur est loup garou
		if roles[ctx.author] == "loup_garou":
			while True:
				#on récupère le vote
				vote = ctx.content
				if members[vote]:
					await ctx.send(f"Vous avez voté pour {vote}")
					break
				else:
					await ctx.send("Le jouer n'a pas été trouvé. Veuillez réessayer.")
"""

bot.run(TOKEN)
