import logging

import discord
from discord.ext.commands import Bot, when_mentioned_or

from .cogs import all_cogs
from .settings import Settings


def run_bot(bot: Bot) -> None:
    settings = Settings()
    bot.run(settings.discord_bot_token)


def init_bot() -> Bot:
    settings = Settings()
    logging.basicConfig(level=settings.log_level)

    # set up bot
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True

    bot = Bot(command_prefix=when_mentioned_or(settings.command_prefix), intents=intents)
    bot.load_extension("slash_cog")

    # register cogs
    for cog in [cog(bot) for cog in all_cogs()]:
        bot.add_cog(cog)

    return bot
