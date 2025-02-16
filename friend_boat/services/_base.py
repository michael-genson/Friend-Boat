import html
from abc import ABC, abstractmethod
from enum import Enum
from io import BufferedIOBase
from typing import IO

from discord import FFmpegPCMAudio, PCMVolumeTransformer

from friend_boat.models._base import MusicItemBase


class AudioStreamEffect(Enum):
    clear = "clear effect"
    chipmunk = "chipmunk"
    deep = "deep"
    void = "void"
    space_odyssey = "space odyssey"
    dark_brandon = "dark brandon"
    demonic = "demonic"
    schizo = "schizophrenia"


class AudioStream(FFmpegPCMAudio):
    def __init__(
        self,
        source: str | BufferedIOBase,
        bitrate: int,
        *,
        start_at: int = 0,
        effect: AudioStreamEffect | None = None,
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

        self._constructor_kwargs = {
            "source": source,
            "bitrate": bitrate,
            "start_at": start_at,
            "effect": effect,
            "executable": executable,
            "pipe": pipe,
            "stderr": stderr,
            "before_options": before_options,
            "options": options,
        }

        self._source = source
        self._position: int = start_at
        """counter of how far into playback we are, in milliseconds"""

        before_options = before_options or {}
        options = options or {}
        if start_at:
            before_options["-ss"] = f"{start_at}ms"

        options.pop("-af", None)
        options.pop("-filter_complex", None)
        options.pop("-map", None)
        if effect and effect is not AudioStreamEffect.clear:
            if effect is AudioStreamEffect.chipmunk:
                options["-af"] = f"atempo=1/2,asetrate={bitrate}*2/1"
            elif effect is AudioStreamEffect.deep:
                options["-af"] = f"asetrate={bitrate}*3/4,atempo=4/3"
            elif effect is AudioStreamEffect.void:
                options["-af"] = f"asetrate={bitrate}*1/2,atempo=2/1"
            elif effect is AudioStreamEffect.space_odyssey:
                options["-filter_complex"] = "aphaser=in_gain=0.3:out_gain=0.6:delay=3.0:decay=0.9:speed=0.75:type=t"
            elif effect is AudioStreamEffect.demonic:
                options["-filter_complex"] = (
                    f"[0:a:0]atempo=1/1[normal];"
                    f"[0:a:0]atempo=0.707107,asetrate={bitrate}*1.414213[transposeup];"
                    f"[0:a:0]asetrate={bitrate}*1/2,atempo=2/1[transposedown];"
                    f"[normal][transposeup][transposedown]amix=inputs=3[a]"
                )
                options["-map"] = "[a]"
            elif effect is AudioStreamEffect.dark_brandon:
                options["-filter_complex"] = (
                    f"aphaser=in_gain=0.3:out_gain=0.6:delay=3.0:decay=0.9:speed=0.75:type=t,"
                    f"asetrate={bitrate}*3/4,atempo=5/4"
                )
            elif effect is AudioStreamEffect.schizo:
                options["-filter_complex"] = (
                    "[0:a:0]channelsplit=channel_layout=mono[left];"
                    "[0:a:0]areverse,channelsplit=channel_layout=mono[right];"
                    "[left][right]join=inputs=2:channel_layout=stereo[a]"
                )
                options["-map"] = "[a]"

        super().__init__(
            source,
            executable=executable,
            pipe=pipe,
            stderr=stderr,
            before_options=self._consolidate_options(before_options),
            options=self._consolidate_options(options),
        )

    @property
    def position(self) -> int:
        """The playback position, in milliseconds"""

        return self._position

    @staticmethod
    def _consolidate_options(options: dict[str, str | None] | None) -> str:
        if not options:
            return ""

        options_strings: list[str] = []
        for k, v in options.items():
            if v is None:
                options_strings.append(k)
            else:
                options_strings.extend([k, v])

        return " ".join(options_strings)

    def apply_effect(self, effect: AudioStreamEffect) -> "AudioStream":
        """Applies the desired effect and returns a new audio stream"""

        kwargs = self._constructor_kwargs.copy()
        kwargs["effect"] = effect
        kwargs["start_at"] = self._position
        return AudioStream(**kwargs)  # type: ignore

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
    async def get_source(
        self, item: MusicItemBase, *, start_at: int = 0, effect: AudioStreamEffect | None = None
    ) -> AudioStream: ...

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
