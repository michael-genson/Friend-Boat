import logging

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: int = logging.ERROR

    # bot config
    command_prefix: str = "/"

    # auth
    discord_bot_token: str = ""
    youtube_api_key: str = ""

    # queue
    max_queue_size: int = 100
