from queue import Empty, Queue
from types import TracebackType
from typing import Any, Callable, Self

from discord import Message, VoiceClient

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
        self.currently_playing_message: Message | None = None
        self.voice_client: VoiceClient | None = None

    async def __aenter__(self) -> Self:
        if not self.voice_client:
            raise Exception("Tried to start player before entering a voice channel")

        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, exc_tb: TracebackType | None
    ) -> None:
        pass

    def add_to_queue(self, item: MusicQueueItem) -> None:
        """Puts an item into the queue. Raises a `MusicQueueFullError` if the queue is full"""

        if self._queue.qsize() > self._max_queue_size:
            raise MusicQueueFullError()

        self._queue.put(item)

    def next(self) -> MusicQueueItem | None:
        """Returns the next item in the queue, if there is one"""

        try:
            return self._queue.get(block=False)
        except Empty:
            return None

    def clear(self) -> None:
        """Clear the queue"""

        self._queue = Queue()

    def skip(self) -> None:
        if self.voice_client:
            self.voice_client.stop()

    def stop(self) -> None:
        self.clear()
        if self.voice_client:
            self.voice_client.stop()

    async def play(self, queue_item: MusicQueueItem, callback: Callable[[Exception | None], Any]) -> None:
        if not self.voice_client:
            raise Exception("Tried to start player before entering a voice channel")

        player = await queue_item.player_service.get_player(queue_item.music)
        self.voice_client.play(player, after=callback)
