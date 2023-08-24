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
        before_options: str | None = None,
        options: str | None = None,
    ) -> None:
        """
        Wrapper around FFmpegPCMAudio to enable additional effects

        start_at: Time to start playback, in milliseconds
        """

        before_options = before_options or ""

        # inject start_at into before_options
        if start_at:
            if "-ss " in before_options or "-sse " in before_options:
                start_at = 0
            else:
                before_options = f"-ss {start_at}ms " + before_options

        super().__init__(
            source, executable=executable, pipe=pipe, stderr=stderr, before_options=before_options, options=options
        )

        self._counter: int = start_at
        """counter of how far into playback we are, in milliseconds"""

    def read(self) -> bytes:
        self._counter += 20  # reads are buffered in 20ms chunks

        return super().read()


class MusicPlayerServiceBase(ABC):
    @abstractmethod
    async def get_source(self, item: MusicItemBase, *, start_at: int = 0) -> AudioStream:
        ...

    async def get_player(self, source: AudioStream) -> PCMVolumeTransformer:
        return PCMVolumeTransformer(source, volume=0.5)

    @staticmethod
    def cln(text: str | None, unescape_html: bool = True) -> str:
        if not text:
            return ""
        else:
            text = text.strip()
            if unescape_html:
                text = html.unescape(text)

            return text
