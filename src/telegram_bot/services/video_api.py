import os
import re
import logging
import tempfile
import shutil
from yt_dlp import YoutubeDL
from .. import config

logger = logging.getLogger(__name__)

def download_video(url):
    """
    Downloads the video from the provided URL.
    WARNING: This function is BLOCKING (Sync). It must be executed in a separate thread.
    """
    if not re.search(r"(youtube|youtu\.be|facebook|instagram|tiktok)", url, re.IGNORECASE):
        raise ValueError("❌ Unsupported or invalid URL.")

    temp_dir = tempfile.mkdtemp()

    cookie_file_path = None
    use_temp_cookie = False

    try:
        if config.COOKIES:
            if os.path.isfile(config.COOKIES):
                cookie_file_path = config.COOKIES
            else:
                fd, cookie_file_path = tempfile.mkstemp(suffix=".txt", text=True)
                with os.fdopen(fd, 'w') as f:
                    f.write(config.COOKIES)
                use_temp_cookie = True

        is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()

        if is_youtube:
            format_spec = (
                "bestvideo[ext=mp4][vcodec^=avc1][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best"
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
            "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                "geo_bypass": True,
        }

        if cookie_file_path:
            ydl_opts["cookiefile"] = cookie_file_path

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
            raise ValueError("🔒 YouTube bloqueó la petición. Las cookies pueden haber expirado o la IP del servidor está en lista negra.")
        raise e

    finally:
        if use_temp_cookie and cookie_file_path and os.path.exists(cookie_file_path):
            try:
                os.remove(cookie_file_path)
            except OSError:
                pass
