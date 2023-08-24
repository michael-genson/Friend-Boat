import html
from abc import ABC, abstractmethod

from discord import FFmpegPCMAudio, PCMVolumeTransformer

from friend_boat.models._base import MusicItemBase


class MusicPlayerServiceBase(ABC):
    @abstractmethod
    async def get_source(self, item: MusicItemBase) -> FFmpegPCMAudio:
        ...

    async def get_player(self, source: FFmpegPCMAudio) -> PCMVolumeTransformer:
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
