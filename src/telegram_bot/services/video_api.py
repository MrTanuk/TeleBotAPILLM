import os
import re
import time
import logging
import tempfile
import shutil
from yt_dlp import YoutubeDL, DownloadError
from .. import config

logger = logging.getLogger(__name__)


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
        'cookiefile': COOKIES,
        'no_warnings': True,
        'noplaylist': True,
        'max_filesize': 50 * 1024 * 1024, # 50MB (Telegram Bot API limit without local server)
        'merge_output_format': 'mp4',
    } 

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
