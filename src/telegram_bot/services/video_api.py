import os
import re
import time
import logging
import tempfile
import shutil
from yt_dlp import YoutubeDL, DownloadError
from .. import config

logger = logging.getLogger(__name__)

# Simple in-memory cache to avoid hammering Supabase
_cookie_cache = {"data": None, "timestamp": 0}

def get_cookies_from_supabase():
    """
    Fetches cookies from Supabase with a 1-hour cache.
    """
    global _cookie_cache
    
    # If cache is fresh (< 1 hour), use it
    if _cookie_cache["data"] and (time.time() - _cookie_cache["timestamp"] < 3600):
        return _cookie_cache["data"]

    if not config.supabase:
        logger.warning("Supabase is not configured. Cookies unavailable.")
        return None

    try:
        response = config.supabase.table("cookies").select("cookies_data").eq("name_media", "Youtube/Instagram").single().execute()
        # Note: supabase-py v2 returns an object with .data
        if response.data and "cookies_data" in response.data:
            cookie_data = response.data["cookies_data"]
            _cookie_cache["data"] = cookie_data
            _cookie_cache["timestamp"] = time.time()
            logger.info("Cookies updated from Supabase.")
            return cookie_data
            
        logger.warning("No cookies found in Supabase.")
        return None
    except Exception as e:
        logger.error("Error fetching cookies: %s", e)
        return None

def download_video(url):
    """
    Downloads the video from the provided URL.
    
    WARNING: This function is BLOCKING (Sync). It must be executed in a separate thread.
    """
    # Basic URL validation
    if not re.search(r'(youtube|youtu\.be|facebook|instagram|tiktok)', url, re.IGNORECASE):
        raise ValueError("❌ Unsupported or invalid URL.")

    temp_dir = tempfile.mkdtemp()
    
    # Intelligent format configuration
    is_youtube = "youtube" in url.lower() or "youtu.be" in url.lower()
    
    # Prioritize MP4 and mobile-compatible codecs (avc1/h264)
    if is_youtube:
        format_spec = 'bestvideo[ext=mp4][vcodec^=avc1][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    else:
        format_spec = 'best[ext=mp4]/bestvideo+bestaudio/best'

    ydl_opts = {
        'outtmpl': f'{temp_dir}/%(id)s.%(ext)s',
        'format': format_spec,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'max_filesize': 50 * 1024 * 1024, # 50MB (Telegram Bot API limit without local server)
        'merge_output_format': 'mp4',
    }

    # Cookie Management
    cookie_file_path = None
    try:
        if is_youtube or "instagram" in url.lower():
            cookie_data = get_cookies_from_supabase()
            if cookie_data:
                # Create temporary cookie file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix='.txt', encoding='utf-8') as tmp:
                    tmp.write(cookie_data)
                    cookie_file_path = tmp.name
                ydl_opts['cookiefile'] = cookie_file_path

        # --- THE DOWNLOAD ---
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if not filename or not os.path.exists(filename):
                # Sometimes prepare_filename fails if formats are merged, look for mp4
                files = [f for f in os.listdir(temp_dir) if f.endswith('.mp4')]
                if files:
                    filename = os.path.join(temp_dir, files[0])
                else:
                    raise RuntimeError("Could not find the downloaded file.")
            
            return filename

    except Exception as e:
        # Cleanup on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        error_msg = str(e).lower()
        if "login" in error_msg or "sign in" in error_msg:
             raise ValueError("🔒 Private content or login required (Cookies might be expired).")
        raise e
        
    finally:
        # Remove cookie file if it was created
        if cookie_file_path and os.path.exists(cookie_file_path):
            os.remove(cookie_file_path)
