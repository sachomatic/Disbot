from datetime import datetime
import logging

import discord
from dotenv import dotenv_values

from game import Jeu, variantes_disponibles
from strings import en as enStrings, fr as frStrings


langStrings = enStrings


logger = logging.getLogger("interface")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("interface.log")
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
# monochrome formatter taken from discord.py
monochrome_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(monochrome_formatter)
console_handler.setFormatter(
    discord.utils._ColourFormatter()
    if discord.utils.stream_supports_colour(console_handler.stream)
    else monochrome_formatter
)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Started logging")

parsed_env = dotenv_values()


class env:
    CLIENT_ID = parsed_env["CLIENT_ID"]
    DISCORD_TOKEN = parsed_env["DISCORD_TOKEN"]
    PUBLIC_KEY = parsed_env["PUBLIC_KEY"]
    _errors: list[tuple[str, str]] = []
    if CLIENT_ID is None:
        _errors.append(("client ID", "CLIENT_ID"))
    if DISCORD_TOKEN is None:
        _errors.append(("Discord token", "DISCORD_TOKEN"))
    if PUBLIC_KEY is None:
        _errors.append(("Public key", "PUBLIC_KEY"))
    if len(_errors) > 0:
        raise ValueError(  # non-euclidean error which can format properly the error
            "".join(
                (
                    "Environment file should have:",
                    *(f'\nthe {_name} set with "{_key}"' for _name, _key in _errors),
                )
            )
        )
assert isinstance(env.CLIENT_ID, str)
assert isinstance(env.DISCORD_TOKEN, str)
assert isinstance(env.PUBLIC_KEY, str)


intents = discord.Intents.default()
intents.message_content = True
permissions = discord.Permissions()
permissions.read_messages = True
permissions.send_messages = True
permissions.mention_everyone = True
permissions.manage_roles = True

jeu = Jeu[discord.Member]()

client = discord.Client(intents=intents)

guild_id = 1195679159821799444
dubug_channel_id = 1400954735472934983
main_channel_id = 1400950833084104744
admin_role_id = 1400981614569193512
guild: discord.Guild
debug_channel: discord.TextChannel
main_channel: discord.TextChannel
everyone: discord.Role
admin_role: discord.Role
players_role: discord.Role


commandsTree = discord.app_commands.CommandTree(
    client,
    allowed_installs=discord.app_commands.AppInstallationType(guild=True, user=False),
)


@commandsTree.command(
    name="await_players", description="Await players to join the game before starting"
)
@discord.app_commands.describe(variant="the variant of the game to use")
@discord.app_commands.choices(
    variant=[
        discord.app_commands.Choice(name=variant, value=variant)
        for variant in variantes_disponibles.keys()
    ]
)
async def command_await_players(
    interaction: discord.Interaction, variant: discord.app_commands.Choice[str]
):
    match jeu.choisir_variante(variant.value):
        case 0:
            _ = await interaction.response.send_message(
                langStrings.command_await_players_result_0.format(
                    variant.value, everyone.mention
                )
            )
            logger.info("Game awaiting for players")
        case 1:
            _ = await interaction.response.send_message(
                langStrings.command_await_players_result_1.format(variant.value)
            )
        case 2:
            _ = await interaction.response.send_message(
                langStrings.command_await_players_result_2, ephemeral=True
            )


@commandsTree.command(
    name="join", description="Join a game when it waits for player only"
)
async def command_join(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(langStrings.command__notInGuild)
        return
    match jeu.ajouter_un_joueur(interaction.user):
        case 0:
            _ = await interaction.response.send_message(
                langStrings.command_join_result_0.format(interaction.user)
            )
            await interaction.user.add_roles(players_role)
        case 1:
            _ = await interaction.response.send_message(
                langStrings.command_join_result_1, ephemeral=True
            )
        case 2:
            _ = await interaction.response.send_message(
                langStrings.command_join_result_2, ephemeral=True
            )


@commandsTree.command(name="see_role")
async def command_see_role(
    interaction: discord.Interaction, user: discord.Member | None = None
):
    if user is None:
        _user = interaction.user
    else:
        _user = user
    if not isinstance(_user, discord.Member):
        _ = await interaction.response.send_message(
            langStrings.command__notInGuild, ephemeral=True
        )
        return
    try:
        role = jeu.joueurs[_user].rôle
        _ = await interaction.response.send_message(
            langStrings.command_see_role_result_0.format(role.nom, role.description),
            ephemeral=True,
        )
    except KeyError:
        _ = await interaction.response.send_message(
            langStrings.command_see_role_result_1, ephemeral=True
        )


@commandsTree.command(name="start", description="Starts the game")
async def command_start(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        _ = await interaction.response.send_message(
            langStrings.command__notInGuild, ephemeral=True
        )
        return
    match jeu.assigner_rôles():
        case 0:
            _ = await interaction.response.send_message(
                langStrings.command_start_result_0.format(players_role.mention)
            )


@commandsTree.command(name="stop", description="Stops the game")
async def command_stop(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        _ = await interaction.response.send_message(langStrings.command__notInGuild)
        return
    match jeu.stop():
        case 0:
            _ = await interaction.response.send_message(langStrings.command_stop_result_0)
            logger.info("Game stopped")
        case 1:
            await interaction.response.send_message(langStrings.command_stop_result_1)


@client.event
async def on_ready():
    global guild
    global debug_channel
    global main_channel
    global everyone
    global admin_role
    global players_role
    global langStrings

    logger.info(f"Logged in as {client.user}")

    _tmp = client.get_guild(guild_id)
    if not isinstance(_tmp, discord.Guild):
        print(f"Error: {guild_id} is not a guild")
        exit(1)
    guild = _tmp
    logger.debug("Bound guild")

    if guild.preferred_locale is discord.Locale.french:
        langStrings = frStrings

    _tmp = guild.get_channel(dubug_channel_id)
    if not isinstance(_tmp, discord.TextChannel):
        print(f"Error: {dubug_channel_id} is not a text channel")
        exit(1)
    debug_channel = _tmp
    logger.debug("Bound debug channel")

    _tmp = guild.get_channel(main_channel_id)
    if not isinstance(_tmp, discord.TextChannel):
        print(f"Error: {main_channel_id} is not a text channel")
        exit(1)
    main_channel = _tmp
    logger.debug("Bound main channel")

    everyone = guild.default_role
    logger.debug("Bound everyone role")

    _tmp = guild.get_role(admin_role_id)
    if not isinstance(_tmp, discord.Role):
        print(f"Error: {admin_role_id} is not a role")
        exit(1)
    admin_role = _tmp
    logger.debug("Bound admin role")

    for _tmp in guild.roles:
        if _tmp.name == "Players":
            players_role = _tmp
    if "PLAYERS_ROLE" not in locals():
        players_role = await guild.create_role(name="Players", hoist=True)
        logger.info("Created players role")
    logger.debug("Bound players role")

    await commandsTree.sync(guild=guild)
    logger.info("Synced commands")


@client.event
async def on_message(message: discord.Message):
    global jeu
    if not isinstance(message.author, discord.Member):
        logger.debug(f"Got MP from {message.author}, ignored")
        return

    splitMSG = message.content.split(" ")

    # Last word auto reply
    ref = message.reference
    if ref is not None:
        msg = ref.cached_message
        if msg is not None:
            if msg.author == client.user:
                await message.reply("I will always have the last word")
                logger.info("A message of the client was replied, replying immediately")

    # ping command
    if splitMSG[0] == "!ping":
        delay = datetime.now(message.created_at.tzinfo) - message.created_at
        s = delay.seconds
        ms = delay.microseconds / 1000
        await message.reply(f"Pong! Delay: {s}s, {ms}ms")
        logger.warning(f"Member {message.author} tested ping, results: {s}s, {ms}ms")
        return

    # await command
    if splitMSG[0] == "!await":
        if admin_role not in message.author.roles:
            await message.reply("You're not allowed to start a new game")
        if len(splitMSG) < 2:
            await message.reply(
                f"You have to specify witch variant of the game you want to use between *{'*, *'.join(variantes_disponibles)}*"
            )
            return
        match jeu.choisir_variante(splitMSG[1]):
            case 0:
                await main_channel.send(
                    f"A new game was created, {everyone.mention} you can join with !join"
                )
            case 1:
                await message.reply(
                    f"Unsupported variant: {splitMSG[1]} ; use one between *{'*, *'.join(variantes_disponibles)}*"
                )
            case 2:
                await message.reply("Impossible to start multiple games")
        return

    # join command
    if splitMSG[0] == "!join":
        match jeu.ajouter_un_joueur(message.author):
            case 0:
                await message.author.add_roles(players_role, reason="Joined the game")
                await message.reply("You joined the game successfully")
            case 1:
                await message.reply("You cannot join because the game already started")
            case 2:
                await message.reply("You cannot join twice")
        return

    # start command
    if splitMSG[0] == "!start":
        if admin_role not in message.author.roles:
            await message.reply("You're not allowed to start the game manually")
        match jeu.assigner_rôles():
            case 0:
                await main_channel.send(f"{players_role.mention}, the game starts")
            case 1:
                await message.reply("The game is not awaiting players")
            case 2:
                await message.reply("There is too much/not enough players")
        return

    # cancel command
    if splitMSG[0] == "!cancel":
        if admin_role not in message.author.roles:
            await message.reply("You're not allowed to cancel the game")
        match jeu.stop():
            case 0:
                del jeu
                jeu = Jeu[discord.Member]()
                await main_channel.send(
                    f"{players_role.mention}, the game is cancelled"
                )
                for member in players_role.members:
                    await member.remove_roles(players_role)
            case 1:
                await message.reply("No game is currently running")


logger.info(
    f"Integrate the bot with this URL: {discord.utils.oauth_url(env.CLIENT_ID, permissions=permissions)}"  # type: ignore[arg-type]
)
client.run(token=env.DISCORD_TOKEN)  # type: ignore[arg-type]
