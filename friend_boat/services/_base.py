import html
from abc import ABC, abstractmethod
from io import BufferedIOBase
from typing import IO

from discord import FFmpegPCMAudio, PCMVolumeTransformer

from friend_boat.models._base import MusicItemBase


class AudioStream(FFmpegPCMAudio):
    def __init__(
        self,
        source: str | BufferedIOBase,
        *,
        start_at: int = 0,
        executable: str = "ffmpeg",
        pipe: bool = False,
        stderr: IO[str] | None = None,
        before_options: dict[str, str | None] | None = None,
        options: dict[str, str | None] | None = None,
    ) -> None:
        """
        Wrapper around FFmpegPCMAudio to enable additional effects

        start_at: Time to start playback, in milliseconds
        """

        before_options = before_options or {}
        if start_at:
            before_options["-ss"] = f"{start_at}ms"

        super().__init__(
            source,
            executable=executable,
            pipe=pipe,
            stderr=stderr,
            before_options=self._consolidate_options(before_options),
            options=self._consolidate_options(options),
        )

        self._position: int = start_at
        """counter of how far into playback we are, in milliseconds"""

    @property
    def position(self) -> int:
        """The playback position, in milliseconds"""

        return self._position

    @staticmethod
    def _consolidate_options(options: dict[str, str | None] | None) -> str:
        """crude options builder"""

        if not options:
            return ""

        options_strings: list[str] = []
        for k, v in options.items():
            if v is None:
                options_strings.append(k)
            else:
                options_strings.extend([k, v])

        return " ".join(options_strings)

    def read(self) -> bytes:
        self._position += 20  # reads are buffered in 20ms chunks

        return super().read()


class AudioPlayer(PCMVolumeTransformer):
    def __init__(self, source: AudioStream, volume: float = 0.5):
        self.source = source

        super().__init__(source, volume)

    @property
    def position(self) -> int:
        """The playback position, in milliseconds"""

        return self.source.position


class MusicPlayerServiceBase(ABC):
    @abstractmethod
    async def get_source(self, item: MusicItemBase, *, start_at: int = 0) -> AudioStream:
        ...

    async def get_player(self, source: AudioStream) -> AudioPlayer:
        return AudioPlayer(source)

    @staticmethod
    def cln(text: str | None, unescape_html: bool = True) -> str:
        if not text:
            return ""
        else:
            text = text.strip()
            if unescape_html:
                text = html.unescape(text)

            return text
