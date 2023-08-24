import logging
import traceback
from collections import defaultdict

from discord import ApplicationContext, Member, VoiceState, option, slash_command
from discord.channel import VocalGuildChannel
from discord.ext.commands import Cog

from friend_boat.models.bots import (
    DiscordCogBase,
    UserNotInServerError,
    UserNotInVoiceChannelError,
    require_server_presence,
)
from friend_boat.models.music import MusicQueueFullError, MusicQueueItem
from friend_boat.models.paginator import SimplePaginator
from friend_boat.models.youtube import NoResultsFoundError
from friend_boat.services.music import MusicQueueService
from friend_boat.services.youtube import YouTubeService

from ..settings import Settings

player_service_by_guild: defaultdict[int, MusicQueueService] = defaultdict(MusicQueueService)


class Music(DiscordCogBase):
    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        """Leave empty voice channels"""

        player_service = player_service_by_guild[member.guild.id]
        if player_service.is_alone:
            await player_service.stop()

    async def cog_command_error(self, ctx: ApplicationContext, error: Exception):
        """Base error handling"""

        if isinstance(error, UserNotInVoiceChannelError):
            await ctx.respond("You must be in a voice channel to use this command", ephemeral=True)
        elif isinstance(error, UserNotInServerError):
            await ctx.respond("You must be in a server to use this command", ephemeral=True)
        else:
            logging.debug(traceback.format_exc())

    ### Music Controls ###

    @require_server_presence()
    @slash_command(
        description="Play a YouTube video, or search for one. If something is already playing, it's added to the queue"
    )
    @option("query", description="a YouTube Video URL or search query")
    @option("skip_ahead", description="how far to skip ahead when starting playback, in seconds")
    async def play(self, ctx: ApplicationContext, query: str, skip_ahead: int = 0):
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
                start_at=skip_ahead * 1000,  # skip_ahead is in seconds, but start_at is in milliseconds
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
    @slash_command(description="Pause the current track")
    async def pause(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.currently_playing:
            await ctx.respond("Nothing is currently playing", ephemeral=True)
        else:
            if player_service.is_paused:
                await player_service.pause()
                await ctx.respond("Paused playback", ephemeral=True)
            else:
                await ctx.respond(
                    'Playback was already paused. To resume playing, use the "/resume" command', ephemeral=True
                )

    @require_server_presence()
    @slash_command(description="Resume the current track, if paused")
    async def resume(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.currently_playing:
            await ctx.respond("Nothing is currently playing", ephemeral=True)
        else:
            await player_service.resume()
            await ctx.respond("Resumed playback", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Skip the current track")
    async def skip(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        async with ctx.typing():
            await player_service.skip()

        await ctx.respond("Skipped", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Stop playing the current track and clear the queue")
    async def stop(self, ctx: ApplicationContext):
        if ctx.guild_id not in player_service_by_guild:
            return await ctx.respond("Nothing is currently playing", ephemeral=True)

        player_service = player_service_by_guild[ctx.guild_id]
        async with ctx.typing():
            await player_service.stop()
            del player_service_by_guild[ctx.guild_id]

        await ctx.respond("Stopped playback and cleared the queue", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Restart the current track")
    async def restart(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.currently_playing:
            await ctx.respond("Nothing is currently playing", ephemeral=True)
        else:
            player_service.toggle_repeat_once(force_on=True)
            await player_service.skip()
            await ctx.respond("Restarted", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Repeat the current track once after it ends")
    async def toggle_repeat(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.currently_playing:
            await ctx.respond("Nothing is currently playing", ephemeral=True)
        else:
            if player_service.toggle_repeat_once():
                await ctx.respond("Okay, this track will be repeated once", ephemeral=True)
            else:
                await ctx.respond("Okay, this track won't repeat", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Loop the current track forever (or at least until you all leave)")
    async def toggle_repeat_forever(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.currently_playing:
            await ctx.respond("Nothing is currently playing", ephemeral=True)
        else:
            if player_service.toggle_repeat_forever():
                await ctx.respond(
                    "Okay, this track will keep playing until everyone leaves, or this command is run again",
                    ephemeral=True,
                )
            else:
                await ctx.respond("Okay, this track won't repeat anymore", ephemeral=True)

    @require_server_presence()
    @slash_command(description="Shuffle the queue")
    async def shuffle(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.queue_size:
            await ctx.respond("Nothing is currently queued", ephemeral=True)
        else:
            player_service.shuffle()
            await ctx.respond("Queue shuffled", ephemeral=True)

    ### Status ###

    @require_server_presence()
    @slash_command(description="Show what's currently playing")
    async def now_playing(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        if not player_service.currently_playing:
            await ctx.respond("Nothing is currently playing", ephemeral=True)
        else:
            text = "Now Playing (Currently Paused):" if player_service.is_paused else "Now Playing:"
            await ctx.respond(text, embed=player_service.currently_playing.embeds.playing, ephemeral=True)

    @require_server_presence()
    @slash_command(description="List everything coming up")
    async def up_next(self, ctx: ApplicationContext):
        player_service = player_service_by_guild[ctx.guild_id]
        pages = player_service.embeds.queue_pages
        if not pages:
            await ctx.respond("Nothing is currently queued", ephemeral=True)
        else:
            settings = Settings()
            await ctx.respond("Here's what's up next:")
            await SimplePaginator(timeout=settings.queue_paginator_timeout).start(ctx, pages=pages)
