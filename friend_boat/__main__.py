#!/usr/bin/python

import argparse
import os

from friend_boat.bots.bot import init_bot, run_bot

parser = argparse.ArgumentParser(prog="FriendBoat", description="A simple music bot for Discord")
parser.add_argument("--discord-token", type=str, help="your Discord Bot Token", required=False)
parser.add_argument(
    "--youtube-api-key", type=str, help="your Google API Key with access to the YouTube Data API v3 ", required=False
)


def main() -> None:
    args = parser.parse_args()
    if args.discord_token:
        os.environ["discord_bot_token"] = args.discord_token
    if args.youtube_api_key:
        os.environ["youtube_api_key"] = args.youtube_api_key

    if not all([os.environ.get("DISCORD_BOT_TOKEN"), os.environ.get("YOUTUBE_API_KEY")]):
        raise Exception(
            "You must provide both a Discord Bot Token and a Google API Key with access to the YouTube Data API v3"
        )

    bot = init_bot()
    run_bot(bot)


if __name__ == "__main__":
    main()
