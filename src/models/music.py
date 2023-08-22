from __future__ import annotations

from dataclasses import dataclass

from discord import Embed, Member, PCMVolumeTransformer, User
from discord.ext.commands import CommandError

from ..services._base import MusicPlayerServiceBase
from ._base import MusicItemBase


@dataclass
class MusicQueueItem:
    player_service: MusicPlayerServiceBase
    music: MusicItemBase
    requestor: Member | User

    _embeds: MusicQueueItemEmbeds | None = None

    @property
    def embeds(self) -> MusicQueueItemEmbeds:
        if not self._embeds:
            self._embeds: MusicQueueItemEmbeds = MusicQueueItemEmbeds(self.music, self.requestor)

        return self._embeds

    async def get_player(self) -> PCMVolumeTransformer:
        return await self.player_service.get_player(self.music)


class MusicQueueItemEmbeds:
    def __init__(self, item: MusicItemBase, author: Member | User) -> None:
        self.item = item
        self.author = author

    @property
    def queued(self) -> Embed:
        embed = Embed(title=self.item.name, description=self.item.description, url=self.item.url)
        embed.set_thumbnail(url=self.item.thumbnail_url)

        return embed

    @property
    def playing(self) -> Embed:
        embed = self.queued
        embed.set_author(name=self.author.display_name, icon_url=self.author.display_avatar.url)

        if self.item.original_query:
            embed.set_footer(text=f"query: {self.item.original_query}")

        return embed


class MusicQueueFullError(CommandError):
    def __init__(self) -> None:
        super().__init__("Queue is full")
