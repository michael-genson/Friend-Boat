from discord.ext.commands import Bot, Cog, CommandError


class DiscordCogBase(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


class NotVoiceChannelError(CommandError):
    def __init__(self, *args: object) -> None:
        super().__init__("Command not received from a voice channel")
