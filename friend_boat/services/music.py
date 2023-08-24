import asyncio
import random
from queue import Empty, Queue
from typing import cast

from discord import Message, VoiceClient
from discord.channel import VocalGuildChannel

from friend_boat.bots.settings import Settings
from friend_boat.models.music import MusicQueueEmbeds, MusicQueueFullError, MusicQueueItem


class MusicQueueService:
    def __init__(self) -> None:
        settings = Settings()
        self._embeds: MusicQueueEmbeds | None = None

        # queue
        self._queue: Queue[MusicQueueItem] = Queue()
        self._max_queue_size = settings.max_queue_size

        # state
        self._currently_playing: MusicQueueItem | None = None
        """The music currently being played"""

        self._currently_playing_message: Message | None = None
        """The message showing the currently playing item"""

        self._voice_client: VoiceClient | None = None
        """The voice client we are connected to while playing"""

        self._repeat_once: bool = False
        self._repeat_forever: bool = False

    @property
    def currently_playing(self) -> MusicQueueItem | None:
        return self._currently_playing

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def is_alone(self) -> bool:
        """Whether or not the bot is in a channel by itself"""

        if not (self._voice_client and self._voice_client.is_connected()):
            # not in a voice channel
            return False

        current_channel = cast(VocalGuildChannel, self._voice_client.channel)
        return len(current_channel.members) <= 1

    @property
    def is_paused(self) -> bool:
        if not self._voice_client:
            return False

        return self._voice_client.is_paused()

    @property
    def current_voice_channel_id(self) -> int | None:
        if not self._voice_client:
            return None
        else:
            return self._voice_client.channel.id  # type: ignore [attr-defined]

    @property
    def embeds(self) -> MusicQueueEmbeds:
        if not self._embeds:
            self._embeds = MusicQueueEmbeds(self._queue)

        return self._embeds

    async def start_playing(self, currently_playing_message: Message, voice_channel: VocalGuildChannel) -> None:
        """Start playing the queue"""

        self._currently_playing_message = currently_playing_message
        await self.switch_voice_channel(voice_channel, skip_current=False)
        return await self._play_next()

    async def switch_voice_channel(self, new_channel: VocalGuildChannel, skip_current=True) -> None:
        """Switch to a new voice channel. Optionally skip what is currently playing"""

        self._voice_client = await new_channel.connect()
        if skip_current and self._currently_playing:
            await self.skip()

    async def _play_next(self, _: Exception | None = None) -> None:
        if not (self._voice_client and self._voice_client.is_connected()):
            return await self.stop()

        if not self._currently_playing or not (self._repeat_once or self._repeat_forever):
            try:
                self._currently_playing = self._queue.get(block=False)
            except Empty:
                return await self.stop()
        if self._repeat_once:
            self._repeat_once = False

        player = await self._currently_playing.get_player()
        loop = asyncio.get_event_loop()
        self._voice_client.play(player, after=lambda ex: asyncio.run_coroutine_threadsafe(self._play_next(ex), loop))

        if self._currently_playing_message:
            await self._currently_playing_message.edit(
                content="Now Playing:", embed=self._currently_playing.embeds.playing
            )

    def clear(self) -> None:
        """Clear the queue"""

        self._queue = Queue()  # TODO: actually clear the queue instead of making a new one
        self._embeds = None  # TODO: this is unnecessary if we properly clear the queue

    async def pause(self) -> None:
        """Pauses playback"""

        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.pause()

    async def resume(self) -> None:
        """Resumes playback, if paused"""

        if self._voice_client and self._voice_client.is_paused():
            self._voice_client.resume()

    async def skip(self) -> None:
        """Ends the current item and proceeds to the next one"""

        self._repeat_once = False
        self._repeat_forever = False
        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()

    def _reset_state(self) -> None:
        self.clear()
        self._currently_playing = None
        self._currently_playing_message = None
        self._voice_client = None

        self._repeat_once = False
        self._repeat_forever = False

    async def stop(self) -> None:
        if self._voice_client:
            try:
                if self._voice_client.is_playing():
                    self._voice_client.stop()
                if self._voice_client.is_connected():
                    await self._voice_client.disconnect()
            except Exception:
                pass

        if self._currently_playing_message:
            try:
                await self._currently_playing_message.delete()
            except Exception:
                pass

        self._reset_state()

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
