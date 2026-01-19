import os
import re
import logging
import tempfile
import shutil
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)


def download_video(url):
    """
    Downloads the video from the provided URL.
    WARNING: This function is BLOCKING. Executed in a separate thread.
    """
    if not re.search(
        r"(youtube|youtu\.be|facebook|instagram|tiktok)", url, re.IGNORECASE
    ):
        raise ValueError("❌ Unsupported or invalid URL.")

    temp_dir = tempfile.mkdtemp()

    try:
        is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()

        if is_youtube:
            # Formato optimizado para evitar archivos muy pesados
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
            "verbose": True,
            "nocheckcertificate": True,
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
                "Accept-Language": "en-US,en;q=0.9",
            },
            "geo_bypass": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if not filename or not os.path.exists(filename):
                files = [f for f in os.listdir(temp_dir) if f.endswith(".mp4")]
                if files:
                    filename = os.path.join(temp_dir, files[0])
                else:
                    raise RuntimeError("Could not find the downloaded file.")

            return filename

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)

        error_msg = str(e).lower()
        if "sign in" in error_msg or "confirm you’re not a bot" in error_msg:
            raise ValueError(
                "🔒 YouTube requiere verificación. Intenta con otro video."
            )
        raise e
