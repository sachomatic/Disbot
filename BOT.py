# bot.py
import os, time,datetime, logging, asyncio,discord
from discord.ext import commands
from dotenv import load_dotenv
from Werewolf_game import Game,Player

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SERVER = os.getenv('DISCORD_SERVER')
PERMISSIONS = os.getenv('DISCORD_PERMISSIONS')

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

overwrite = discord.PermissionOverwrite()
overwrite.read_messages = False
overwrite.manage_channels = True
overwrite.manage_roles = True
overwrite.manage_channels = True

bot = commands.Bot(command_prefix='!',intents = intents,overwrite=overwrite)

og_time = time.time()

d = {0:'monday',1:'tuesdays',2:'wednesdays',3:'thursdays',4:'friday',5:'saturday',6:'sunday'}

og_days = d[datetime.datetime.now().weekday()]
og_day_nb = datetime.datetime.now().day
og_hours = datetime.datetime.now().hour
og_minutes = datetime.datetime.now().minute

async def on_ready(c,*args,**kwargs):
	guild_count = 0

	for guild in bot.guilds:
		await c.send(f"- id:{guild.id} name:{guild.name}")

		guild_count += 1
	print("Ready!")

	await c.send("DisDawn is in " + str(guild_count) + " guilds.")

def get_decimal_numbers(number):
    number_str = str(number)
    decimal_index = number_str.find('.')
    if decimal_index == -1:
        return ''

    return float(number_str[decimal_index:])

@bot.command(name='create_game')
async def create_game(ctx,*args,**kwargs):
	global game_start
	global player_lst
	await ctx.send('@everyone Starting game in 1 minute. Use !start to start now and !join to join the game! There must be at least 4 players to start the game and maximum 10 players')
	game_start = True
	player_lst = []
	for i in range(60):
		await asyncio.sleep(1)
		if game_start == False:
			return
	await start_game(ctx)

async def obtain_channel_list():
	channels_to_obtain = ["village","werewolf","stealer","president","cupidon","witch"]

@bot.command(name='start')
async def start_game(ctx,*args,**kwargs):
	global game_start
	global player_lst
	global game
	try:
		if game_start != True:
			await ctx.send("Game is not created. Please use !create_game.")
			return
		else:
			game_start = False
			game = Game(player_lst,ctx.guild)
			await ctx.send("@everyone Starting game with:",delete_after = 5)
			for pl in game.player_list:
				await ctx.send(f'-{pl.name}',delete_after = 5)
			game.give_roles()
			for player in player_lst:
				await player.discord.send(f"You are a {player.role}")
			await ctx.send("Please wait while the roles are resetting.")
			try:	
				await game.reset(ctx)
			except:
				await ctx.send("Error : roles couldn't be resetted, game will continue but might crash")
			await ctx.send("Let's go!")
			await game.assign_roles(ctx)
			await game.start(ctx)

	except NameError as error:
		await ctx.send(f"Game is not created. Please use !create_game.")
		logging.exception("")
		return
	except KeyError:
		logging.exception("")
		await ctx.send("Not enough players to start game")
	except Exception as error:
		logging.exception('')
		await ctx.send("An error occured, causing the game to crash. Please restart it.")

async def search_channel(name,server):
	for channel in server.channels:
		if str(channel.name) == str(name):
			return channel

async def get_roles():
	roles_list = ["1","2","3","4","5","6","7"]
	fn_roles_list = []
	try:
		if game:
			for role in game.server:
				if role.name in roles_list:
					fn_roles_list.append(role)
			return fn_roles_list
	except:
		return False

#Specials commands

@bot.command(name='kill')
async def kill(ctx,*args,**kwargs):
	global game
	ws = game.get_element_by_attribute(game.player_list,"role","werewolf","name")
	try:
		player = game.get_element_by_attribute(ws,"name",ctx.author.display_name)[0]
		if player.state == 0:
			try:
				name = args[0]
				await ctx.send(f"Voted for {name}")
			except:
				await ctx.send("Player name missing.")
				return
			game.vote(name)
			await game.transfer_response(name)
		else:
			await ctx.send("You are dead.")
	except:
		await ctx.send("You are not a werewolf.")
	
@bot.command(name="enamorate")
async def enamorate(ctx,*args,**kwargs):
	global game
	player = game.get_element_by_attribute(game.player_list,"role","cupidon","name")[0]
	if ctx.author.display_name == player.name and player.state == 0:
		try:
			lover1 = args[0]
			lover2 = args[1]
			if lover1 == lover2:
				await ctx.send("Lovers can't be the same")
				return
		except:
			return
		await game.transfer_response((lover1,lover2))
	else:
		await ctx.send("You are not cupidon or are dead.")

@bot.command(name="steal")
async def steal(ctx,*args,**kwargs):
	global game
	player = game.get_element_by_attribute(game.player_list,"role","stealer","name")[0]
	if ctx.author.display_name == player and player.state == 0:
		try:
			stealed = args[0]
			if ctx.author == stealed:
				await ctx.send("You can't steal yourself.")
				return
			else:
				await game.transfer_response(stealed)
		except:
			await ctx.send("No player chosen.")
			return
	else:
		await ctx.send("You are not a stealer or are dead.")

@bot.command("hunt")
async def hunt(ctx,*args,**kwargs):
	global game
	player = game.get_element_by_attribute(game.player_list,"role","hunt")[0]
	if ctx.author.display_name == player.name and player.state == 0:
		try:
			hunted = args[0]
			if ctx.author == hunted:
				await ctx.send("You can't shot yourself.")
				return
			else:
				await game.transfer_response(hunted)
		except:
			await ctx.send("No player chosen.")
			return
	else:
		await ctx.send("You are not a hunter or have not the chance to hunt yet..")

@bot.command(name="save")
async def steal(ctx,*args,**kwargs):
	global game
	player = game.get_element_by_attribute(game.player_list,"role","witch")[0]
	if ctx.author.display_name == player.name and player.state == 0:
		await game.transfer_response(["save",None])
	else:
		await ctx.send("You are not a witch or are dead.")

@bot.command(name="poison")
async def steal(ctx,*args,**kwargs):
	global game
	player = game.get_element_by_attribute(game.player_list,"role","witch","name")[0]
	if ctx.author.display_name == player and player.state == 0:
		try:
			target = args[0]
			if ctx.author == target:
				await ctx.send("You can't kill yourself.")
				return
			else:
				await game.transfer_response(["kill",target])
		except:
			await ctx.send("No player chosen.")
			return
	else:
		await ctx.send("You are not a witch or are dead.")

@bot.command(name="vote")
async def vote(ctx,*args,**kwargss):
	global game
	user = game.get_element_by_attribute(game.player_list,"name",ctx.author.display_name)
	if user.state == True:
		if game.night_day == "day":
			try:
				voted = args[0]
			except:
				await ctx.send("No player chosen.")
				return
			game.vote(voted)
		else:
			ctx.sed("It's not the time to vote yet.")
	else:
		await ctx.send("You're dead, you can't vote")


@bot.command(name='setup')
async def setup(ctx):
	await ctx.send("Setting up")
	temp = Game('me')
	await ctx.send("Creating channels...")
	ver = False
	for channel in ctx.guild.channels:
		if str(channel) == 'werewolf':
			ver = True
	if ver == False:
		await ctx.guild.create_text_channel('werewolf')
	ver = False
	for channel in ctx.guild.channels:
		if str(channel) == 'village':
			ver = True
	if ver == False:
		await ctx.guild.create_text_channel('village')
	for role in temp.spe_roles:
		temp_ver = False
		for channel in ctx.guild.channels:
			if str(channel) == role:
				temp_ver = True
		if temp_ver == False:
			await ctx.send(f"Creating {role}")
			await ctx.guild.create_text_channel(role)
		else:
			await ctx.send(f"{role} is already created.")
	#for i in range(1,10):
		#await create_role(ctx,i)
	await ctx.send('done')
	guild = ctx.guild

@bot.command(name="cancel")
async def stop_game(ctx):
	global game_start
	game_start = False
	await ctx.send("Game stopped")

@bot.command("hello")
async def dm_me(ctx,*args,**kwargs):
	print(ctx.author.id)

@bot.command(name='join')
async def join_list(ctx,*args,**kwargs):
	global player_lst
	player_lst.append(Player(ctx.author.display_name,ctx.author))
	await ctx.send(f"{ctx.author} just joined the game!")

@bot.command(name='fill')
async def fill_game(ctx,*args,**kwargs):
	global player_lst
	try:
		fill_number = int(args[0])
	except:
		fill_number = 7
	for i in range(fill_number):
		await join_list(ctx)

@bot.command(name='see_commands')
async def show_commands(ctx,*args,**kwargs):
	"""
	Command to see all the commands
	"""
	for cmd in bot.commands:
		await ctx.send(cmd)

@bot.command(name = "stop_bot")
async def stop_bot(ctx,*args,**kwargs):
	await  ctx.send("Stopping...")
	quit()

@bot.command(name = "delete_all")
async def delete_all_messages(ctx,*args,**kwargs):
	global cancel
	count = 0
	await ctx.send("DELETING ALL MESSAGE @everyone. Type !cancel to cancel.")
	#try:
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
		except:
			pass
	await ctx.send("Finished", delete_after = 5)
	#except Limi:
		#await ctx.send("Rate limit reached. Try again later.")

@bot.command(name="test")
async def test(ctx,*args,**kwargs):
	local_time = time.time() - og_time
	t_hours = local_time /60/60
	tampon = get_decimal_numbers(t_hours)
	hours = int(t_hours)
	t_minutes = tampon*60
	tampon = get_decimal_numbers(t_minutes)
	minutes = int(t_minutes)
	seconds = int(tampon*60)
	await ctx.send(f"Hello {ctx.author}. Running since {og_days} the {og_day_nb}, at {og_hours}h{og_minutes}m, for {hours}:{minutes}:{seconds}. Server list :")
	await on_ready(c=ctx)
	await ctx.send("Members of the guild:")
	for members in ctx.guild.members:
		await ctx.send(f"-{members}")

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