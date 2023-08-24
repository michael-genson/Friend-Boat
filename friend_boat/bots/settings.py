import logging

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: int = logging.ERROR
    debug: bool = False

    # bot config
    command_prefix: str = "/"

    # auth
    discord_bot_token: str = ""
    youtube_api_key: str = ""

    # queue
    max_queue_size: int = 100
    queue_paginator_page_size: int = 5
    queue_paginator_timeout: int = 60
    """How long until the queue paginator embed list times out, in seconds"""
