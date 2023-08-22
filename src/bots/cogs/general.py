from discord import ApplicationContext, Member, slash_command
from discord.ext.commands import command, is_owner

from src.models.bots import DiscordCogBase


class General(DiscordCogBase):
    @slash_command(name="ping", description="Ping me!")
    async def ping(self, ctx: ApplicationContext):
        """Ping me!"""

        await ctx.respond("Pong!")

    @command()
    @is_owner()
    async def sync(self, ctx: ApplicationContext):
        if isinstance(ctx.author, Member):
            await self.bot.sync_commands(force=True, guild_ids=[ctx.author.guild.id])
