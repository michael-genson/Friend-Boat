import asyncio
from queue import Empty, Queue
from typing import cast

from discord import Message, VoiceClient
from discord.channel import VocalGuildChannel

from src.bots.settings import Settings
from src.models.music import MusicQueueFullError, MusicQueueItem


class MusicQueueService:
    def __init__(self) -> None:
        settings = Settings()

        # queue
        self._queue: Queue[MusicQueueItem] = Queue()
        self._max_queue_size = settings.max_queue_size

        # state
        self.currently_playing: MusicQueueItem | None = None
        """The music currently being played"""

        self._currently_playing_message: Message | None = None
        """The message showing the currently playing item"""

        self._voice_client: VoiceClient | None = None
        """The voice client we are connected to while playing"""

    @property
    def is_alone(self) -> bool:
        """Whether or not the bot is in a channel by itself"""

        if not (self._voice_client and self._voice_client.is_connected()):
            # not in a voice channel
            return False

        current_channel = cast(VocalGuildChannel, self._voice_client.channel)
        return len(current_channel.members) <= 1

    @property
    def current_voice_channel_id(self) -> int | None:
        if not self._voice_client:
            return None
        else:
            return self._voice_client.channel.id  # type: ignore [attr-defined]

    async def start_playing(self, currently_playing_message: Message, voice_channel: VocalGuildChannel) -> None:
        """Start playing the queue"""

        self._currently_playing_message = currently_playing_message
        await self.switch_voice_channel(voice_channel, skip_current=False)
        return await self._play_next()

    async def switch_voice_channel(self, new_channel: VocalGuildChannel, skip_current=True) -> None:
        """Switch to a new voice channel. Optionally skip what is currently playing"""

        self._voice_client = await new_channel.connect()
        if skip_current and self.currently_playing:
            await self.skip()

    async def _play_next(self, _: Exception | None = None) -> None:
        if not (self._voice_client and self._voice_client.is_connected()):
            return await self.stop()

        try:
            self.currently_playing = self._queue.get(block=False)
        except Empty:
            return await self.stop()

        player = await self.currently_playing.get_player()
        loop = asyncio.get_event_loop()
        self._voice_client.play(player, after=lambda ex: asyncio.run_coroutine_threadsafe(self._play_next(ex), loop))

        if self._currently_playing_message:
            await self._currently_playing_message.edit(
                content="Now Playing:", embed=self.currently_playing.embeds.playing
            )

    def clear(self) -> None:
        """Clear the queue"""

        self._queue = Queue()

    async def skip(self) -> None:
        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()

    async def stop(self) -> None:
        self.clear()
        self.currently_playing = None

        if self._voice_client:
            if self._voice_client.is_playing():
                self._voice_client.stop()
            if self._voice_client.is_connected():
                await self._voice_client.disconnect()

            self._voice_client = None

        if self._currently_playing_message:
            await self._currently_playing_message.delete()

    def add_to_queue(self, item: MusicQueueItem) -> None:
        """Puts an item into the queue. Raises a `MusicQueueFullError` if the queue is full"""

        if self._queue.qsize() > self._max_queue_size:
            raise MusicQueueFullError()

        self._queue.put(item)
