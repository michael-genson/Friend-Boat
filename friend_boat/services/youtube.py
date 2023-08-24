import asyncio
import os
import re
import shutil
from tempfile import TemporaryDirectory
from typing import cast

import yt_dlp  # type: ignore
from pyyoutube import Api, SearchListResponse, SearchResult, Video, VideoListResponse  # type: ignore

from friend_boat.models._base import MusicItemBase
from friend_boat.models.youtube import SearchType, YoutubeVideo

from ._base import AudioStream, MusicPlayerServiceBase

youtube_video_id_pattern = re.compile(
    r"^(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com"
    r"\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$"
)


class YouTubeService(MusicPlayerServiceBase):
    def __init__(self, api_key: str) -> None:
        self.api = Api(api_key=api_key)
        self._temp_dir = TemporaryDirectory().name

    def __del__(self):
        try:
            shutil.rmtree(self._temp_dir)
        except FileNotFoundError:
            pass

    @staticmethod
    def get_youtube_video_id_from_url(url: str | None) -> str | None:
        """Extracts the video id from a YouTube video URL, if the URL is valid"""

        if not url:
            return None

        matches: list[tuple[str]] = re.findall(youtube_video_id_pattern, url)
        if not matches:
            return None
        else:
            return matches[0][0]

    @staticmethod
    def build_url_from_video_id(video_id: str) -> str:
        return f"https://www.youtube.com/watch?v={video_id}"

    def search_video(self, query: str) -> YoutubeVideo | None:
        """Searches YouTube for a video using a query string and returns the URL of that video, if found"""

        response: SearchListResponse | VideoListResponse | None = None
        video_id = self.get_youtube_video_id_from_url(query)
        if video_id:
            # try to find the video by searching by id
            response = self.api.get_video_by_id(video_id=video_id)
            if not (response and response.items):
                response = None

        if not response:
            # try to find the video by querying as a search term
            response = self.api.search(q=query, search_type=SearchType.video.value)
            if not response:
                return None

        result: SearchResult | Video | None = None
        for item in response.items:
            if item.snippet.liveBroadcastContent and item.snippet.liveBroadcastContent != "none":
                continue

            result = item
            break

        if not (result and result.snippet):
            return None

        thumbnail_url = (
            result.snippet.thumbnails.default.url
            if result.snippet.thumbnails and result.snippet.thumbnails.default
            else None
        )

        if not result.id:
            return None
        elif isinstance(result, SearchResult):
            url = self.build_url_from_video_id(result.id.videoId)
        else:
            url = self.build_url_from_video_id(result.id)

        return YoutubeVideo(
            url=url,
            name=self.cln(result.snippet.title),
            description=self.cln(result.snippet.description),
            thumbnail_url=thumbnail_url,
            original_query=query,
        )

    def get_ytdl(self) -> yt_dlp.YoutubeDL:
        return yt_dlp.YoutubeDL(
            {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(self._temp_dir, "%(extractor)s-%(id)s-%(title)s.%(ext)s"),
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

    async def get_source(self, item: MusicItemBase, *, start_at: int = 0) -> AudioStream:
        if not isinstance(item, YoutubeVideo):
            raise Exception("This service does not support this item")

        loop = asyncio.get_event_loop()
        ytdl = self.get_ytdl()
        data: dict = await loop.run_in_executor(None, lambda: ytdl.extract_info(item.url, download=False))
        if "entries" in data:
            # take first item from a playlist
            data = cast(dict, data["entries"][0])

        return AudioStream(
            data["url"],
            start_at=start_at,
            options="-vn",
            # prevents early stream terminations (requires ffmpeg >= 3): https://github.com/Rapptz/discord.py/issues/315
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        )
