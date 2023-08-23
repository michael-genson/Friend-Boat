from enum import Enum

from discord.ext.commands import CommandError

from ._base import MusicItemBase


class SearchType(Enum):
    channel = "channel"
    playlist = "playlist"
    video = "video"


class YoutubeVideo(MusicItemBase):
    ...


class NoResultsFoundError(CommandError):
    def __init__(self, query: str, *args: object) -> None:
        super().__init__(f'No results found for query: "{query}"')
