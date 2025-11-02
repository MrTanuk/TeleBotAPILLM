import os
import re
import time
import logging
import tempfile
import shutil
from yt_dlp import YoutubeDL, DownloadError
from .. import config

_cookie_cache = {"data": None, "timestamp": 0}
logger = logging.getLogger(__name__)

def get_cookies_from_supabase():
    """Fetches cookie data from the Supabase database."""
    if _cookie_cache["data"] and (time.time() - _cookie_cache["timestamp"] < 3600):
        logger.info("Cookies loaded successfully from cache.")
        return _cookie_cache["data"]

    if not config.supabase:
        logger.warning("Supabase is not configured. Cannot fetch cookies.", exc_info=True)
        return None
    try:
        response = config.supabase.table("cookies").select("cookies_data").eq("name_media", "Youtube/Instagram").single().execute()
        if response.data and "cookies_data" in response.data:
            logger.info("Cookies loaded successfully from Supabase.")
            cookie_data = response.data["cookies_data"]
            
            _cookie_cache["data"] = cookie_data
            _cookie_cache["timestamp"] = time.time()
            
            return cookie_data
        logger.warning("No cookies found for 'Youtube/Instagram' in Supabase.", exc_info=True)
        return None
    except Exception as e:
        logger.error("Error fetching cookies from Supabase: %s", e, exc_info=True)
        return None


def download_video(url):
    """Downloads a video from a given URL, but does NOT clean up the temporary file."""
    url_pattern = re.compile(
        r'^(https?://)?(?:www\.)?'
        r'(?:'
        r'(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w\-]+|'
        r'facebook\.com|fb\.watch|instagram\.com|instagr\.am|tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com'
        r')', re.IGNORECASE
    )
    if not url_pattern.match(url):
        raise ValueError("❌ Invalid URL. Supported sites: YouTube, Facebook, Instagram, TikTok.")

    temp_dir = tempfile.mkdtemp()
    
    is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()
    is_instagram = "instagram.com" in url.lower() or "instagr.am" in url.lower()
    if is_youtube:
        format_spec = 'bestvideo[ext=mp4][vcodec^=avc1][height<=480]+bestaudio/best'
    elif is_instagram:
        format_spec = 'best[ext=mp4]/bestvideo+bestaudio'
    elif "tiktok.com" in url.lower() or "vm.tiktok.com" in url.lower():
        format_spec = 'bestvideo[ext=mp4][vcodec^=avc1][height<=720]+bestaudio/best'
    else:  
        format_spec = '(bestvideo[vcodec^=avc1][height<=720]+bestaudio)/best'
    MAX_SIZE_MB = 49.5
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1_000_000
    
    cookie_file_path = None
    try:
        ydl_opts = {
            'outtmpl': f'{temp_dir}/%(id)s.%(ext)s',
            'format': format_spec,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': None,
            'noplaylist': True,
            'max_filesize': MAX_SIZE_BYTES,
            'merge_output_format': 'mp4',
            'socket_timeout': 30,
        }
    
        if is_youtube or is_instagram:
            cookie_data = get_cookies_from_supabase()
            if cookie_data:
                with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix='.txt', encoding='utf-8') as tmp_cookie_file:
                    tmp_cookie_file.write(cookie_data)
                    cookie_file_path = tmp_cookie_file.name
                ydl_opts['cookiefile'] = cookie_file_path

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if not filename or not os.path.exists(filename):
                raise RuntimeError("Download process completed, but the final video file is missing.")
            
            file_size = os.path.getsize(filename)
            if file_size > MAX_SIZE_BYTES:
                raise ValueError(f"❌ Video too large ({file_size/1_000_000:.1f}MB > {MAX_SIZE_MB}MB limit)")

            return filename

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        error_msg = str(e).lower()
        if "login" in error_msg or "age-restricted" in error_msg or "private" in error_msg:
             raise ValueError("🔒 This video is private or age-restricted. Updated cookies may be required.")
        if isinstance(e, DownloadError):
            raise ValueError(f"❌ Download failed: {str(e).split(':')[-1].strip()}")
        logger.error("Unexpected error in video API: %s", str(e), exc_info=True)
        raise e
    finally:
        if cookie_file_path and os.path.exists(cookie_file_path):
            os.remove(cookie_file_path)
