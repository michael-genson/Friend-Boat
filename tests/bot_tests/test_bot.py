from friend_boat.bots.bot import init_bot
from friend_boat.bots.cogs import all_cogs


def test_healthcheck():
    bot = init_bot()
    for cog in all_cogs():
        assert isinstance(bot.cogs.get(cog.__cog_name__), cog)
