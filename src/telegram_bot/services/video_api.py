import os
import re
import logging
import tempfile
import shutil
import requests
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)

COBALT_API_URL = "https://api.cobalt.tools"


def download_video(url):
    """
    Try to download via Cobalt (External API). If it fails, use local yt-dlp with mobile camouflage.
    """
    if not re.search(
        r"(youtube|youtu\.be|facebook|instagram|tiktok|twitter|x\.com)",
        url,
        re.IGNORECASE,
    ):
        raise ValueError("❌ Link not supported.")

    temp_dir = tempfile.mkdtemp()
    filename = os.path.join(temp_dir, "video.mp4")

    try:
        logger.info(f"🔄 Attempting download via Cobalt...")

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        payload = {
            "url": url,
            "vQuality": "720",
            "filenamePattern": "basic",
            "isAudioOnly": False,
        }

        response = requests.post(
            f"{COBALT_API_URL}/api/json", json=payload, headers=headers, timeout=15
        )

        if response.status_code != 200:
            logger.warning(f"⚠️ Cobalt error {response.status_code}: {response.text}")
            raise ConnectionError("Cobalt API Error")

        data = response.json()

        if "url" in data:
            video_url = data["url"]
            with requests.get(video_url, stream=True) as r:
                r.raise_for_status()
                with open(filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            logger.info("✅ Successful download via Cobalt")
            return filename
        else:
            logger.warning(f"⚠️ Unexpected Cobalt response: {data}")

    except Exception as e:
        logger.warning(f"⚠️ Cobalt failed ({str(e)}), switching to local yt-dlp...")

    try:
        is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()

        if is_youtube:
            format_spec = (
                "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            )
        else:
            format_spec = "best[ext=mp4]/bestvideo+bestaudio/best"

        ydl_opts = {
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
                "tiktok": {
                    "app_version": ["30.0.0"],
                    "manifest_app_version": ["30.0.0"],
                },
            },
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            },
            "geo_bypass": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get("title", "Unknown Video")
            logger.info(f"📥 Downloaded via yt-dlp: {video_title}")

            downloaded_files = [f for f in os.listdir(temp_dir) if f != "video.mp4"]

            if downloaded_files:
                return os.path.join(temp_dir, downloaded_files[0])
            else:
                raise RuntimeError("Downloaded file not found on disk.")

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        error_msg = str(e).lower()
        if "sign in" in error_msg:
            raise ValueError("🔒 It couldn't download video")
        raise e
