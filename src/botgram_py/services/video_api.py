import asyncio
import logging
import os
import re
import shutil
import tempfile
from typing import Any

import httpx
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

COBALT_API_URL = "https://api.cobalt.tools"
# Asynchronous client for Cobalt
http_client = httpx.AsyncClient(timeout=15.0)


def _download_yt_dlp(url: str, temp_dir: str) -> str:
    """Isolated synchronous function to run in a thread."""
    is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()
    format_spec = (
        "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        if is_youtube
        else "best[ext=mp4]/bestvideo+bestaudio/best"
    )

    ydl_opts: Any = {
        "outtmpl": f"{temp_dir}/%(id)s.%(ext)s",
        "format": format_spec,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": 50 * 1024 * 1024,
        "merge_output_format": "mp4",
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "ios"],
                "player_skip": ["web", "tv"],
            },
            "tiktok": {"app_version": ["30.0.0"], "manifest_app_version": ["30.0.0"]},
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"
        },
        "geo_bypass": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info: Any = ydl.extract_info(url, download=True)
        video_title = info.get("title", "Unknown Video") if info else "Unknown Video"
        logger.info(f"📥 Downloaded via yt-dlp: {video_title}")

        downloaded_files = [f for f in os.listdir(temp_dir) if f != "video.mp4"]
        if downloaded_files:
            return os.path.join(temp_dir, downloaded_files[0])
        raise RuntimeError("Downloaded file not found on disk.")


async def download_video(url: str) -> str:
    """Video download: Try Async Cobalt first. If it fails, delegate to yt-dlp in a thread."""
    if not re.search(
        r"(youtube|youtu\.be|facebook|instagram|tiktok|twitter|x\.com)",
        url,
        re.IGNORECASE,
    ):
        raise ValueError("❌ Link not supported.")

    temp_dir = tempfile.mkdtemp()
    filename = os.path.join(temp_dir, "video.mp4")

    try:
        logger.info("🔄 Attempting download via Cobalt...")
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        payload: dict[str, str | bool] = {
            "url": url,
            "vQuality": "720",
            "filenamePattern": "basic",
            "isAudioOnly": False,
        }

        response = await http_client.post(
            f"{COBALT_API_URL}/api/json", json=payload, headers=headers
        )

        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            if "url" in data:
                async with http_client.stream("GET", data["url"]) as r:
                    r.raise_for_status()
                    with open(filename, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=8192):
                            f.write(chunk)

                logger.info("✅ Successful download via Cobalt")
                return filename

        logger.warning(
            f"⚠️ Cobalt returned unexpected response or error: {response.status_code}"
        )

    except Exception as e:
        logger.warning(f"⚠️ Cobalt failed ({str(e)}), switching to local yt-dlp...")

    try:
        return await asyncio.to_thread(_download_yt_dlp, url, temp_dir)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if "sign in" in str(e).lower():
            raise ValueError("🔒 It couldn't download video (Sign in required)")
        raise e
