from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, TypeVar

from discord import Embed, Member, User
from discord.ext.commands import CommandError

from friend_boat.bots.settings import Settings
from friend_boat.services._base import AudioPlayer, AudioStream, AudioStreamEffect, MusicPlayerServiceBase

from ._base import MusicItemBase

T = TypeVar("T")


@dataclass
class MusicQueueItem:
    player_service: MusicPlayerServiceBase
    music: MusicItemBase
    requestor: Member | User

    source: AudioStream | None = None
    """The AudioStream source, if it already exists"""
    start_at: int = 0
    """When to start playback, in milliseconds"""

    effect: AudioStreamEffect | None = None

    _embeds: MusicQueueItemEmbeds | None = None
    _player: AudioPlayer | None = None

    @property
    def embeds(self) -> MusicQueueItemEmbeds:
        if not self._embeds:
            self._embeds = MusicQueueItemEmbeds(self.music, self.requestor)

        return self._embeds

    @property
    def position(self) -> int:
        """The playback position, in milliseconds"""

        return self._player.position if self._player else 0

    async def load_player(self, start_at: int | None = None, effect: AudioStreamEffect | None = None) -> AudioPlayer:
        if not self._player:
            if start_at is None:
                start_at = self.start_at
            if effect is None:
                effect = self.effect

            if not self.source:
                self.source = await self.player_service.get_source(self.music, start_at=self.start_at, effect=effect)

            self._player = await self.player_service.get_player(self.source)

        return self._player

    def copy(self, **kwargs) -> MusicQueueItem:
        attrs = {
            k: kwargs[k] if k in kwargs else getattr(self, k)
            for k in ["player_service", "music", "requestor", "start_at", "effect"]
        }

        return MusicQueueItem(**attrs)


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
    def __init__(self, queue_items: list[MusicQueueItem]) -> None:
        self._items = queue_items

    @staticmethod
    def chunk_list(list_: list[T], chunk_size: int) -> Generator[list[T], list[T], None]:
        """Break a list into smaller list of size `chunk_size`"""
        for i in range(0, len(list_), chunk_size):
            yield list_[i : i + chunk_size]

    def _build_queue_item_text(self, item: MusicQueueItem) -> str:
        return f"**{item.music.name}**, requested by *{item.requestor.display_name}*"

    def _build_queue_item_page(self, items: list[MusicQueueItem]) -> Embed:
        return Embed(
            title="Up Next" if len(items) == 1 else f"Up Next ({len(items)} items queued)",
            description="\n---\n".join([self._build_queue_item_text(item) for item in items]),
        )

    @property
    def queue_pages(self) -> list[Embed]:
        """A list of embeds, each representing one page of queue items"""

        settings = Settings()
        return [
            self._build_queue_item_page(chunk)
            for chunk in self.chunk_list(self._items, settings.queue_paginator_page_size)
        ]


class MusicQueueFullError(CommandError):
    def __init__(self) -> None:
        super().__init__("Queue is full")
