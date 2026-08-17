from friend_boat.models.bots import DiscordCogBase

from .general import General
from .music import Music


def all_cogs() -> list[type[DiscordCogBase]]:
    return [General, Music]
