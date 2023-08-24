from discord import ApplicationContext
from discord.errors import CheckFailure
from discord.ext.commands import Bot, Cog, check


class DiscordCogBase(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


class UserNotInServerError(CheckFailure):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "User is not in a server")


class UserNotInVoiceChannelError(UserNotInServerError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or "User is not in a voice channel")


def require_server_presence():
    async def wrapper(ctx: ApplicationContext) -> bool:
        if not ctx.guild:
            raise UserNotInServerError()
        else:
            return True

    return check(wrapper)
