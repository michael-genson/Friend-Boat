from abc import ABC
from dataclasses import dataclass

from discord import Embed


@dataclass
class MusicItemBase(ABC):
    url: str
    name: str
    description: str

    thumbnail_url: str | None = None
    original_query: str | None = None

    @property
    def embed(self) -> Embed:
        embed = Embed(title=self.name, description=self.description, url=self.url)
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)
        if self.original_query:
            embed.set_footer(text=f"original query by: {self.original_query}")

        return embed
