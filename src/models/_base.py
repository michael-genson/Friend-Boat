from abc import ABC
from dataclasses import dataclass


@dataclass
class MusicItemBase(ABC):
    url: str
    name: str
    description: str

    thumbnail_url: str | None = None
    original_query: str | None = None
