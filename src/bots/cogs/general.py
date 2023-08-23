from discord import ApplicationContext, Member, slash_command
from discord.ext.commands import command, is_owner

from src.models.bots import DiscordCogBase


class General(DiscordCogBase):
    @slash_command(name="ping", description="Ping me!")
    async def ping(self, ctx: ApplicationContext):
        """Ping me!"""

        await ctx.respond(f"Pong! ({self.bot.latency*100:.2f}ms)")

    @command()
    @is_owner()
    async def sync(self, ctx: ApplicationContext):
        if isinstance(ctx.author, Member):
            await self.bot.sync_commands(force=True, guild_ids=[ctx.author.guild.id])
