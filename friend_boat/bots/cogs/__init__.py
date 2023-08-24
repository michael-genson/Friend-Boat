from typing import Type

from friend_boat.models.bots import DiscordCogBase

from .general import General
from .music import Music


def all_cogs() -> list[Type[DiscordCogBase]]:
    return [General, Music]
