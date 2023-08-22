import html
from abc import ABC, abstractmethod

from discord import PCMVolumeTransformer

from src.models._base import MusicItemBase


class MusicPlayerServiceBase(ABC):
    @abstractmethod
    async def get_player(self, item: MusicItemBase) -> PCMVolumeTransformer:
        ...

    @staticmethod
    def cln(text: str | None, unescape_html: bool = True) -> str:
        if not text:
            return ""
        else:
            text = text.strip()
            if unescape_html:
                text = html.unescape(text)

            return text
