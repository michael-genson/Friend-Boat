import asyncio
from typing import cast

import yt_dlp  # type: ignore
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from pyyoutube import Api, SearchListResponse  # type: ignore

from ..models._base import MusicItemBase
from ..models.youtube import SearchType, YoutubeVideo
from ._base import MusicPlayerServiceBase

ytdl = yt_dlp.YoutubeDL(
    {
        "format": "bestaudio/best",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0",  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }
)


class YTDLSource(PCMVolumeTransformer):
    # https://github.com/Rapptz/discord.py/blob/master/examples/basic_voice.py

    # Suppress noise about console usage from errors
    yt_dlp.utils.bug_reports_message = lambda: ""

    def __init__(self, source: FFmpegPCMAudio, *, data: dict, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")


class YouTubeService(MusicPlayerServiceBase):
    def __init__(self, api_key: str) -> None:
        self.api = Api(api_key=api_key)

    @staticmethod
    def build_url_from_video_id(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    @classmethod
    async def build_ytdl_source(
        cls, video: YoutubeVideo, *, loop: asyncio.AbstractEventLoop | None = None, stream=False
    ) -> YTDLSource:
        if not loop:
            loop = asyncio.get_event_loop()

        data: dict = await loop.run_in_executor(None, lambda: ytdl.extract_info(video.url, download=not stream))
        if "entries" in data:
            # take first item from a playlist
            data = cast(dict, data["entries"][0])

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return YTDLSource(FFmpegPCMAudio(filename, options="-vn"), data=data)

    def search_video(self, query: str) -> YoutubeVideo | None:
        """Searches YouTube for a video using a query string and returns the URL of that video, if found"""

        results: SearchListResponse = self.api.search(q=query, search_type=SearchType.video.value)
        if not results.items:
            return None

        result = results.items[0]
        thumbnail_url = (
            result.snippet.thumbnails.default.url
            if result.snippet.thumbnails and result.snippet.thumbnails.default
            else None
        )

        return YoutubeVideo(
            url=self.build_url_from_video_id(result.id.videoId),
            name=self.cln(result.snippet.title),
            description=self.cln(result.snippet.description),
            thumbnail_url=thumbnail_url,
            original_query=query,
        )

    async def get_player(self, item: MusicItemBase) -> PCMVolumeTransformer:
        if not isinstance(item, YoutubeVideo):
            raise Exception("This service does not support this item")

        return await self.build_ytdl_source(item)
