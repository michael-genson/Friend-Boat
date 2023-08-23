from __future__ import annotations

from dataclasses import dataclass
from queue import Queue
from typing import Generator, TypeVar

from discord import Embed, Member, PCMVolumeTransformer, User
from discord.ext.commands import CommandError

from src.bots.settings import Settings
from src.services._base import MusicPlayerServiceBase

from ._base import MusicItemBase

T = TypeVar("T")


@dataclass
class MusicQueueItem:
    player_service: MusicPlayerServiceBase
    music: MusicItemBase
    requestor: Member | User

    _embeds: MusicQueueItemEmbeds | None = None

    @property
    def embeds(self) -> MusicQueueItemEmbeds:
        if not self._embeds:
            self._embeds = MusicQueueItemEmbeds(self.music, self.requestor)

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
            embed.set_footer(text=f'query: "{self.item.original_query}"')

        return embed


class MusicQueueEmbeds:
    def __init__(self, queue: Queue[MusicQueueItem]) -> None:
        self._music_queue = queue

    @staticmethod
    def chunk_list(list_: list[T], chunk_size: int) -> Generator[list[T], list[T], None]:
        """Break a list into smaller list of size `chunk_size`"""
        for i in range(0, len(list_), chunk_size):
            yield list_[i : i + chunk_size]

    def _build_queue_item_text(self, item: MusicQueueItem) -> str:
        return f"**{item.music.name}**, requested by *{item.requestor.display_name}*"

    def _build_queue_item_page(self, items: list[MusicQueueItem]) -> Embed:
        return Embed(
            title="Up Next",
            description="\n---\n".join([self._build_queue_item_text(item) for item in items]),
        )

    @property
    def queue_pages(self) -> list[Embed]:
        """A list of embeds, each representing one page of queue items"""

        settings = Settings()

        all_items: list[MusicQueueItem] = list(self._music_queue.queue)
        return [
            self._build_queue_item_page(chunk)
            for chunk in self.chunk_list(all_items, settings.queue_paginator_page_size)
        ]


class MusicQueueFullError(CommandError):
    def __init__(self) -> None:
        super().__init__("Queue is full")
