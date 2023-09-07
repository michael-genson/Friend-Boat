import asyncio
import random
from queue import Empty, Queue
from typing import cast

from discord import Bot, Message, VoiceClient
from discord.channel import VocalGuildChannel

from friend_boat.bots.settings import Settings
from friend_boat.models.music import MusicQueueEmbeds, MusicQueueFullError, MusicQueueItem
from friend_boat.services._base import AudioStreamEffect


class MusicQueueService:
    def __init__(self, bot: Bot, guild_id: int) -> None:
        self.bot = bot
        self.guild_id = guild_id

        settings = Settings()

        # queue
        self._queue: Queue[MusicQueueItem] = Queue()
        self._max_queue_size = settings.max_queue_size

        # state
        self._currently_playing: MusicQueueItem | None = None
        """The music currently being played"""

        self._hot_swap_currently_playing: MusicQueueItem | None = None
        """The music to play immediately after the current item stops"""

        self._next_item_to_play: MusicQueueItem | None = None
        """The next item to play, ignoring the queue"""

        self._currently_playing_message: Message | None = None
        """The message showing the currently playing item"""

        self._applied_effect: AudioStreamEffect | None = None
        self._repeat_once: bool = False
        self._repeat_forever: bool = False

    def _get_voice_client(self) -> VoiceClient | None:
        guild = self.bot.get_guild(self.guild_id)
        if not guild:
            return None
        else:
            if isinstance(guild.voice_client, VoiceClient):
                return guild.voice_client
            else:
                return None

    def _reset_state(self) -> None:
        self.clear()

        self._currently_playing = None
        self._hot_swap_currently_playing = None
        self._next_item_to_play = None
        self._currently_playing_message = None

        self._applied_effect = None
        self._repeat_once = False
        self._repeat_forever = False

    @property
    def currently_playing(self) -> MusicQueueItem | None:
        return self._currently_playing

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def is_alone(self) -> bool:
        """Whether or not the bot is in a channel by itself"""

        voice_client = self._get_voice_client()
        if not (voice_client and voice_client.is_connected()):
            # not in a voice channel
            return False

        current_channel = cast(VocalGuildChannel, voice_client.channel)
        return len(current_channel.members) <= 1

    @property
    def is_paused(self) -> bool:
        voice_client = self._get_voice_client()
        if not voice_client:
            return False

        return voice_client.is_paused()

    @property
    def current_voice_channel_id(self) -> int | None:
        voice_client = self._get_voice_client()
        if not voice_client:
            return None
        else:
            return voice_client.channel.id  # type: ignore [attr-defined]

    @property
    def embeds(self) -> MusicQueueEmbeds:
        queue_items = list(self._queue.queue)
        if self._next_item_to_play:
            queue_items.insert(0, self._next_item_to_play)

        return MusicQueueEmbeds(queue_items)

    async def start_playing(self, currently_playing_message: Message, voice_channel: VocalGuildChannel) -> None:
        """Start playing the queue"""

        self._currently_playing_message = currently_playing_message
        await self.switch_voice_channel(voice_channel, skip_current=False)
        return await self._play_next()

    async def switch_voice_channel(self, new_channel: VocalGuildChannel, skip_current=True) -> None:
        """Switch to a new voice channel. Optionally skip what is currently playing"""

        voice_client = self._get_voice_client()
        if voice_client and voice_client.is_connected():
            await voice_client.move_to(new_channel)
        else:
            await new_channel.connect()

        if skip_current and self._currently_playing:
            await self.skip()

    async def _start_voice_client(self, item: MusicQueueItem, client: VoiceClient) -> None:
        player = await item.load_player()
        loop = asyncio.get_event_loop()
        client.play(player, after=lambda ex: asyncio.run_coroutine_threadsafe(self._play_next(ex), loop))

    async def _trigger_hot_swap(self, old_item: MusicQueueItem, *, timeskip: int | None = None, **kwargs) -> None:
        voice_client = self._get_voice_client()
        if not (voice_client and voice_client.is_connected()):
            return

        self._hot_swap_currently_playing = old_item.copy(**kwargs)

        # pre-load the player so it's ready faster
        if timeskip is None:
            timeskip = 1000  # hot-swapping takes about a second, so this makes the transition more seamless

        await self._hot_swap_currently_playing.load_player(start_at=old_item.position + timeskip)
        voice_client.stop()

    async def _play_next(self, ex: Exception | None = None) -> None:
        if ex:
            raise

        voice_client = self._get_voice_client()
        if not (voice_client and voice_client.is_connected()):
            return await self.stop()

        if self._currently_playing and (self._repeat_once or self._repeat_forever):
            self._next_item_to_play = self._currently_playing.copy(start_at=0)
            self._repeat_once = False

        if self._hot_swap_currently_playing:
            # short circuit the play logic and immediately engage the hot swap item
            self._currently_playing = self._hot_swap_currently_playing
            self._hot_swap_currently_playing = None
            return await self._start_voice_client(self._currently_playing, voice_client)

        try:
            self._currently_playing = self._next_item_to_play or self._queue.get(block=False)
            self._currently_playing.effect = self._applied_effect
            self._next_item_to_play = None
        except Empty:
            return await self.stop()

        await self._start_voice_client(self._currently_playing, voice_client)
        if self._currently_playing_message:
            await self._currently_playing_message.edit(
                content="Now Playing:", embed=self._currently_playing.embeds.playing
            )

    def clear(self) -> None:
        """Clear the queue"""

        self._queue.queue.clear()

    async def pause(self) -> None:
        """Pauses playback"""

        voice_client = self._get_voice_client()
        if voice_client and voice_client.is_playing():
            voice_client.pause()

    async def resume(self) -> None:
        """Resumes playback, if paused"""

        voice_client = self._get_voice_client()
        if voice_client and voice_client.is_paused():
            voice_client.resume()

    async def seek(self, interval: int) -> None:
        """
        Skips ahead or behind in a track, in milliseconds

        If going too far back, the track will start from the beginning.
        If going too far forward, the track will end immediately
        """

        if not self._currently_playing:
            return

        await self._trigger_hot_swap(self._currently_playing, timeskip=self._currently_playing.position + interval)

    def set_next_item(self, item: MusicQueueItem) -> None:
        """Set the next item to be played, ignoring the queue"""

        self._next_item_to_play = item

    async def skip(self) -> None:
        """Ends the current item and proceeds to the next one"""

        self._repeat_once = False
        self._repeat_forever = False

        voice_client = self._get_voice_client()
        if voice_client and voice_client.is_playing():
            voice_client.stop()

    async def stop(self) -> None:
        voice_client = self._get_voice_client()
        if voice_client:
            try:
                if voice_client.is_playing():
                    voice_client.stop()
                if voice_client.is_connected():
                    await voice_client.disconnect()
            except Exception:
                pass

        if self._currently_playing_message:
            try:
                await self._currently_playing_message.delete()
            except Exception:
                pass

        self._reset_state()

    async def apply_effect(self, effect: AudioStreamEffect) -> None:
        if not (self._currently_playing and self._currently_playing.source):
            return

        self._applied_effect = effect
        # TODO: passing the effect twice is redundant, we should fix the API so we can pass it just once
        await self._trigger_hot_swap(
            self._currently_playing, source=self._currently_playing.source.apply_effect(effect), effect=effect
        )

    def add_to_queue(self, item: MusicQueueItem) -> None:
        """Puts an item into the queue. Raises a `MusicQueueFullError` if the queue is full"""

        if self._queue.qsize() > self._max_queue_size:
            raise MusicQueueFullError()

        self._queue.put(item)

    def toggle_repeat_once(self, force_on=False) -> bool:
        self._repeat_once = True if force_on else not self._repeat_once
        return self._repeat_once

    def toggle_repeat_forever(self, force_on=False) -> bool:
        self._repeat_forever = True if force_on else not self._repeat_forever
        return self._repeat_forever

    def shuffle(self) -> None:
        random.shuffle(self._queue.queue)
