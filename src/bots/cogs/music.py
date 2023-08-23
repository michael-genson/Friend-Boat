from collections import defaultdict

from discord import ApplicationContext, Member, VoiceState, option, slash_command
from discord.channel import VocalGuildChannel
from discord.ext.commands import Cog

from src.models.bots import DiscordCogBase, UserNotInServerError, UserNotInVoiceChannelError, require_server_presence
from src.models.music import MusicQueueFullError, MusicQueueItem
from src.models.youtube import NoResultsFoundError
from src.services.music import MusicQueueService
from src.services.youtube import YouTubeService

from ..settings import Settings

player_service_by_guild: defaultdict[int, MusicQueueService] = defaultdict(MusicQueueService)


class Music(DiscordCogBase):
    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        """
        Leave empty voice channels
        """

        player_service = player_service_by_guild[member.guild.id]
        if player_service.is_alone:
            await player_service.stop()

    @require_server_presence()
    @slash_command(
        description="Play a YouTube video, or search for one. If something is already playing, it's added to the queue"
    )
    @option("query", description="a YouTube Video URL or search query")
    async def play(self, ctx: ApplicationContext, query: str):
        # make sure the command was issued from a user in a voice channel
        if (
            isinstance(ctx.author, Member)
            and isinstance(ctx.author.voice, VoiceState)
            and isinstance(ctx.author.voice.channel, VocalGuildChannel)
        ):
            voice_channel = ctx.author.voice.channel
        else:
            voice_channel = None

        if not (voice_channel and ctx.guild):
            raise UserNotInVoiceChannelError()

        # find the youtube video
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

        await ctx.respond("Queued:", embed=music_item.embeds.queued, ephemeral=True)

        # queue up the youtube video and start playback if nothing else is playing
        player_service = player_service_by_guild[ctx.guild.id]
        player_service.add_to_queue(music_item)

        if not player_service.currently_playing:
            currently_playing_message = await ctx.send("Initializing...")
            self.bot.loop.create_task(player_service.start_playing(currently_playing_message, voice_channel))
        elif player_service.current_voice_channel_id != voice_channel.id:
            await player_service.switch_voice_channel(voice_channel)

    @play.error
    async def play_error(self, ctx: ApplicationContext, ex: Exception):
        if isinstance(ex, NoResultsFoundError):
            await ctx.respond(
                "Sorry, no results found for that video. Please try another video or search term", ephemeral=True
            )
        elif isinstance(ex, MusicQueueFullError):
            await ctx.respond("Sorry, the queue is currently full", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Skip the current Youtube video and go to the next one")
    async def skip(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        async with ctx.typing():
            await player_service.skip()

        await ctx.respond("Skipped", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Stop playing the current Youtube video and clear the queue")
    async def stop(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        async with ctx.typing():
            await player_service.stop()

        await ctx.respond("Stopped playback and cleared queue", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Show what's currently playing")
    async def now_playing(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.currently_playing:
            await ctx.respond("Nothing is currently playing", ephemeral=True)
        else:
            await ctx.respond("Now Playing:", embed=player_service.currently_playing.embeds.playing)

    async def cog_command_error(self, ctx: ApplicationContext, error: Exception):
        if isinstance(error, UserNotInVoiceChannelError):
            return await ctx.respond("You must be in a voice channel to use this command", ephemeral=True)
        elif isinstance(error, UserNotInServerError):
            return await ctx.respond("You must be in a server to use this command", ephemeral=True)
