from datetime import datetime
import logging
from typing import TypedDict

import discord
from dotenv import dotenv_values

from game import Jeu  # , variantes_disponibles
from strings import en as enStrings, fr as frStrings


class CustomBreaker(Exception):
    pass


# TODO: logging for all instances
logger = logging.getLogger("interface")
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler("interface-new.log")
file_handler.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
# monochrome formatter taken from discord.py
monochrome_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(monochrome_formatter)
console_handler.setFormatter(
    discord.utils._ColourFormatter()  # pyright:ignore[reportPrivateUsage] # only patch with entire login code please
    if discord.utils.stream_supports_colour(console_handler.stream)
    else monochrome_formatter
)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Started logging")

parsed_env = dotenv_values()


# TODO: clean this code
class env:
    CLIENT_ID: str | None = parsed_env["CLIENT_ID"]
    DISCORD_TOKEN: str | None = parsed_env["DISCORD_TOKEN"]
    PUBLIC_KEY: str | None = parsed_env["PUBLIC_KEY"]
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
                    *(
                        f'\nthe {_name} set with the key "{_key}"'
                        for _name, _key in _errors
                    ),
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
permissions.manage_channels = True

client = discord.Client(intents=intents)


class GuildVariables(TypedDict):
    langStrings: type[enStrings | frStrings]
    jeu: Jeu[discord.Member]
    game_channel: discord.TextChannel
    debug_channel: discord.TextChannel
    player_role: discord.Role
    admin_role: discord.Role


guildsVariables = dict[discord.Guild, GuildVariables]()


class NotInAGuild(Exception):
    pass


async def getGuildFrom(
    discordObject: discord.Interaction | discord.Message,
) -> tuple[discord.Guild, GuildVariables]:
    if isinstance(discordObject, discord.Interaction):
        if not isinstance(discordObject.user, discord.Member):
            logger.debug("Got Interaction from user %s", discordObject.user)
            _ = await discordObject.response.send_message(
                enStrings.command__notInGuild, ephemeral=True
            )
            raise NotInAGuild
        assert discordObject.guild is not None
        return discordObject.guild, guildsVariables[discordObject.guild]
    elif isinstance(discordObject, discord.Message):
        if not isinstance(discordObject.author, discord.Member):
            logger.debug("Got MP from user %s", discordObject.author)
            raise NotInAGuild
        assert discordObject.guild is not None
        return discordObject.guild, guildsVariables[discordObject.guild]
    raise TypeError(discordObject)


async def setupGuild(guild: discord.Guild):
    gv = guildsVariables[guild] = {}  # pyright:ignore[reportArgumentType]
    gv["langStrings"] = (
        frStrings if guild.preferred_locale is discord.Locale.french else enStrings
    )
    gv["jeu"] = Jeu[discord.Member]()
    filePath = "guildIDs/" + str(guild.id)
    try:
        try:
            content = open(filePath, "tr")
        except FileNotFoundError:
            logger.info("Guild config not found")
            raise CustomBreaker
        lines = content.read().splitlines()
        content.close()
        if len(lines) != 4:
            logger.warning("Guild config have %d lines instead of 4", len(lines))
            raise CustomBreaker
        _ = guild.get_channel(int(lines[0]))
        if type(_) is not discord.TextChannel:
            raise CustomBreaker
        gv["game_channel"] = _
        _ = guild.get_channel(int(lines[1]))
        if type(_) is not discord.TextChannel:
            raise CustomBreaker
        gv["debug_channel"] = _
        _ = guild.get_role(int(lines[2]))
        if type(_) is not discord.Role:
            raise CustomBreaker
        gv["admin_role"] = _
        _ = guild.get_role(int(lines[3]))
        if type(_) is not discord.Role:
            raise CustomBreaker
        gv["player_role"] = _
    except CustomBreaker:
        logger.info("Setup instance")
        category = await guild.create_category("Werewolf game")
        gv["game_channel"] = await category.create_text_channel("Principale")
        gv["debug_channel"] = await category.create_text_channel("Débogage")
        gv["player_role"] = await guild.create_role(
            reason="Automatic, for the Werewolf game",
            name="Joueurs",
            hoist=True,
            mentionable=True,
        )
        gv["admin_role"] = await guild.create_role(
            reason="Automatic, for the Werewolf game",
            name="Administrateurs",
            mentionable=True,
        )
        with open(filePath, "tw") as file:
            _ = file.write(
                "\n".join(
                    (
                        str(gv["game_channel"].id),
                        str(gv["debug_channel"].id),
                        str(gv["player_role"].id),
                        str(gv["admin_role"].id),
                    )
                )
            )
    await gv["debug_channel"].set_permissions(guild.default_role, view_channel=False)
    await gv["debug_channel"].set_permissions(gv["admin_role"], view_channel=True)
    for member in gv["player_role"].members:
        await member.remove_roles(gv["player_role"])


@client.event
async def on_ready():
    _ = await commandTree.sync()
    for guild in client.guilds:
        await setupGuild(guild)


@client.event
async def on_guild_join(guild: discord.Guild):
    await setupGuild(guild)


@client.event
async def on_guild_leave(guild: discord.Guild):
    gv = guildsVariables[guild]
    _ = gv["jeu"].stop()
    del gv


commandTree = discord.app_commands.CommandTree(
    client,
    allowed_installs=discord.app_commands.AppInstallationType(guild=True, user=False),
)


@commandTree.command(
    name="await_players",
    description="Await players to join a new game before starting",
)
@discord.app_commands.describe(variant="the variant of the game to use")
# @discord.app_commands.choices(
#     variant=[
#         discord.app_commands.Choice(name=variant, value=variant)
#         for variant in variantes_disponibles.keys()
#     ]
# )
async def command_await_players(interaction: discord.Interaction, variant: str):
    guild, gv = await getGuildFrom(interaction)
    match gv["jeu"].choisir_variante(variant):
        case 0:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_await_players_result_0.format(
                    variant, guild.roles[0].mention
                )
            )
            logger.info("Game awaiting for players")
        case 1:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_await_players_result_1.format(variant),
                ephemeral=True,
            )
        case 2:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_await_players_result_2, ephemeral=True
            )


@commandTree.command(
    name="join", description="Join a game when it waits for player only"
)
async def command_join(interaction: discord.Interaction):
    gv = (await getGuildFrom(interaction))[1]
    assert isinstance(interaction.user, discord.Member)
    match gv["jeu"].ajouter_un_joueur(interaction.user):
        case 0:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_join_result_0.format(interaction.user)
            )
            _ = await interaction.user.add_roles(gv["player_role"])
        case 1:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_join_result_1, ephemeral=True
            )
        case 2:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_join_result_2, ephemeral=True
            )
        case _:
            pass


@commandTree.command(name="wwg_ping")
@discord.app_commands.allowed_installs(True, True)
async def command_ping(interaction: discord.Interaction):
    delay = datetime.now(interaction.created_at.tzinfo) - interaction.created_at
    s = delay.seconds
    ms = delay.microseconds / 1000
    _ = await interaction.response.send_message(
        f"Pong! Delay: {s}s, {ms}ms", ephemeral=True
    )
    logger.warning("Member %s tested ping, results: %ds, %dms", interaction.user, s, ms)


@commandTree.command(name="see_role")
async def command_see_role(
    interaction: discord.Interaction, user: discord.Member | None = None
):
    gv = (await getGuildFrom(interaction))[1]
    if user is None:
        _user = interaction.user
    else:
        _user = user
    if not isinstance(_user, discord.Member):
        _ = await interaction.response.send_message(
            gv["langStrings"].command__notInGuild, ephemeral=True
        )
        return
    try:
        role = gv["jeu"].joueurs[_user].rôle
        _ = await interaction.response.send_message(
            gv["langStrings"].command_see_role_result_0.format(
                role.nom, role.description
            ),
            ephemeral=True,
        )
    except KeyError:
        _ = await interaction.response.send_message(
            gv["langStrings"].command_see_role_result_1, ephemeral=True
        )


@commandTree.command(name="start", description="Starts the game")
async def command_start(interaction: discord.Interaction):
    gv = (await getGuildFrom(interaction))[1]
    match gv["jeu"].assigner_rôles():
        case 0:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_start_result_0.format(
                    gv["player_role"].mention
                )
            )
        case _:
            pass


@commandTree.command(name="stop", description="Stops the game")
async def command_stop(interaction: discord.Interaction):
    gv = (await getGuildFrom(interaction))[1]
    match gv["jeu"].stop():
        case 0:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_stop_result_0
            )
            logger.info("Game stopped")
        case 1:
            _ = await interaction.response.send_message(
                gv["langStrings"].command_stop_result_1
            )
        case _:
            pass


@client.event
async def on_message(message: discord.Message):
    ref = message.reference
    if ref is not None:
        msg = ref.cached_message
        if msg is not None:
            if msg.author == client.user:
                _ = await message.reply("I will always have the last word")
                logger.info(
                    "A message of the client was replied by %s, replying immediately",
                    message.author,
                )


logger.info(
    "Integrate the bot with this URL: %s",
    discord.utils.oauth_url(env.CLIENT_ID, permissions=permissions),
)
client.run(token=env.DISCORD_TOKEN)
