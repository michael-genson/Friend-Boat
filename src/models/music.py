from dataclasses import dataclass

from discord import Embed, Member, User
from discord.ext.commands import CommandError

from ..services._base import MusicPlayerServiceBase
from ._base import MusicItemBase


@dataclass
class MusicQueueItem:
    player_service: MusicPlayerServiceBase
    music: MusicItemBase
    requestor: Member | User

    @property
    def embed(self) -> Embed:
        return self.music.embed


class MusicQueueFullError(CommandError):
    def __init__(self) -> None:
        super().__init__("Queue is full")