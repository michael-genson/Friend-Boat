import asyncio
import traceback
from collections import defaultdict

from discord import ApplicationContext, Guild, Member, VoiceState, slash_command
from discord.channel import VocalGuildChannel
from discord.ext.commands import Cog

from src.models.bots import DiscordCogBase, NotVoiceChannelError
from src.models.music import MusicQueueFullError, MusicQueueItem
from src.models.youtube import NoResultsFoundError
from src.services.music import MusicQueueService
from src.services.youtube import YouTubeService

from ..settings import Settings

player_service_by_guild: defaultdict[int, MusicQueueService] = defaultdict(MusicQueueService)


class Music(DiscordCogBase):
    def _handle_play_next(self, ex: Exception | None, guild: Guild) -> None:
        if ex:
            raise ex

        asyncio.run_coroutine_threadsafe(self._play_next(guild), self.bot.loop)

    async def _play_next(self, guild: Guild) -> None:
        """
        Play the next item in the queue

        Calls itself recursively
        """

        async with player_service_by_guild[guild.id] as player_service:
            if not player_service.voice_client:
                return

            if not player_service.voice_client.is_playing():
                next_item = player_service.next()
                if not next_item:
                    player_service.currently_playing = None
                    if player_service.voice_client:
                        await player_service.voice_client.disconnect()
                        player_service.voice_client = None

                        if player_service.currently_playing_message:
                            await player_service.currently_playing_message.delete()
                            player_service.currently_playing_message = None

                    return

                await player_service.play(next_item, lambda ex: self._handle_play_next(ex, guild))
                if player_service.currently_playing_message:
                    await player_service.currently_playing_message.edit(content="Now Playing:", embed=next_item.embed)

                player_service.currently_playing = next_item

    async def start_playing(self, guild: Guild) -> None:
        """Join a voice channel and start playing the queue"""

        return await self._play_next(guild)

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        """
        Leave empty voice channels
        """

        player_service = player_service_by_guild[member.guild.id]
        if not (player_service.voice_client and player_service.voice_client.is_connected()):
            return

        # stubs are wrong, this is a channel
        if len(player_service.voice_client.channel.members) == 1:  # type: ignore [attr-defined]
            player_service.stop()

    @slash_command(
        description="Play a YouTube video, or search for one. If something is already playing, it's added to the queue"
    )
    async def play(self, ctx: ApplicationContext, query: str):
        # TODO: this method is doing way too much and needs to be cleaned up

        if (
            isinstance(ctx.author, Member)
            and isinstance(ctx.author.voice, VoiceState)
            and isinstance(ctx.author.voice.channel, VocalGuildChannel)
        ):
            voice_channel = ctx.author.voice.channel
        else:
            voice_channel = None

        if not (voice_channel and ctx.guild):
            raise NotVoiceChannelError()

        async with ctx.typing():
            settings = Settings()
            yt_service = YouTubeService(settings.youtube_api_key)

            yt_video = yt_service.search_video(query)
            if not yt_video:
                raise NoResultsFoundError(query)

            music_item = MusicQueueItem(
                player_service=yt_service,
                music=yt_video,
                requestor=ctx.author,
            )

        await ctx.respond("Queued:", embed=music_item.embed)

        player_service = player_service_by_guild[ctx.guild.id]
        player_service.add_to_queue(music_item)

        if (
            player_service.voice_client
            and player_service.voice_client.channel.id != voice_channel.id  # type: ignore [attr-defined]
        ):
            player_service.voice_client = await voice_channel.connect()

        elif not player_service.voice_client:
            player_service.voice_client = await voice_channel.connect()

            player_service.currently_playing_message = await ctx.send("Initializing...")
            await self.start_playing(ctx.guild)
            await ctx.respond("Thanks for listening!")

    @play.error
    async def play_error(self, ctx: ApplicationContext, ex: Exception):
        if isinstance(ex, NotVoiceChannelError):
            await ctx.respond("You must be in a voice channel to play something")
        elif isinstance(ex, NoResultsFoundError):
            await ctx.respond("Sorry, no results found for that video. Please try another video or search term")
        elif isinstance(ex, MusicQueueFullError):
            await ctx.respond("Sorry, the queue is currently full")
        else:
            traceback.print_exc()
            await ctx.respond("Sorry, something went wrong")

    @slash_command(description="Skip the current Youtube video and go to the next one")
    async def skip(self, ctx: ApplicationContext):
        if not ctx.guild:
            return

        player_service = player_service_by_guild[ctx.guild.id]
        player_service.skip()
        await ctx.respond("Skipped")

    @slash_command(description="Stop playing the current Youtube video and clear the queue")
    async def stop(self, ctx: ApplicationContext):
        if not ctx.guild:
            return

        player_service = player_service_by_guild[ctx.guild.id]
        player_service.stop()
        await ctx.respond("Stopping playback and clearing queue")
