import logging

import discord
from discord.ext.commands import Bot, when_mentioned_or

from .cogs import all_cogs
from .settings import Settings

logging.basicConfig(level=logging.INFO)


def init_bot() -> None:
    # set up bot
    settings = Settings()
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True

    bot = Bot(command_prefix=when_mentioned_or(settings.command_prefix), intents=intents)
    bot.load_extension("slash_cog")

    # register cogs
    for cog in [cog(bot) for cog in all_cogs()]:
        bot.add_cog(cog)

    # run bot
    bot.run(settings.discord_bot_token)