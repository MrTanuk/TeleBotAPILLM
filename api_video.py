import os
import re
import logging
import tempfile
from yt_dlp import YoutubeDL
from yt_dlp import DownloadError

logger = logging.getLogger(__name__)

def download_video(url):
    # Enhanced URL validation pattern
    url_pattern = re.compile(
        r'^(https?://)?(?:www\.)?'
        r'(?:'
        #r'(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w\-]+|'  # YouTube patterns
        r'(?:facebook\.com|fb\.watch)/(?:reel|watch|videos|share)/[^/]+|'  # Facebook patterns
        r'(?:instagram\.com|instagr\.am)/(?:reels?|p)/[\w\-]+'  # Instagram patterns
        r')',
        re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        raise ValueError("❌ Invalid URL. Facebook, and Instagram videos are supported")

    # Platform-specific format selection
    #if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        format_spec = 'bestvideo[ext=mp4][vcodec^=avc1][height<=480]+bestaudio/best'  # YouTube optimized
    if "instagram.com" in url.lower() or "instagr.am" in url.lower():
        format_spec = 'best[ext=mp4]/bestvideo+bestaudio'  # Instagram specific handling
    else:  # Facebook
        format_spec = '(bestvideo[vcodec^=avc1][height<=720]+bestaudio)/best'  # Facebook optimized

    MAX_SIZE_MB = 45
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1_000_000

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'outtmpl': f'{tmpdir}/%(id)s.%(ext)s',  # Temporary output template
                'format': format_spec,
                'quiet': True,  # Disable debug output
                'no_warnings': True,
                'cookiefile': None,
                'noplaylist': True,
                'max_filesize': MAX_SIZE_BYTES,
                'merge_output_format': 'mp4',  # Force MP4 container
                'socket_timeout': 30,
                'retries': 10,
                'fragment_retries': 10,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': (
                        'https://www.instagram.com/' 
                        if "instagram" in url.lower() 
                        else 'https://www.facebook.com/'
                    )
                },
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',  # Ensure MP4 output
                    'when': 'post_process'
                }],
                'extractor_args': {
                    'instagram': {
                        'format_sort': ['quality']},
                    'facebook': {
                        'video_formats': 'sd'}
                },
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                # Extract video info and download
                info = ydl.extract_info(url, download=True)
                
                # Verify downloaded file
                filename = ydl.prepare_filename(info)
                if not os.path.exists(filename):
                    raise RuntimeError("Downloaded file not found")
                
                # Size validation
                file_size = os.path.getsize(filename)
                if file_size > MAX_SIZE_BYTES:
                    os.remove(filename)  # Cleanup oversized files
                    raise ValueError(
                        f"❌ Video too large ({file_size/1_000_000:.1f}MB > "
                        f"{MAX_SIZE_MB}MB limit)"
                    )

                # Read and return video bytes
                with open(filename, 'rb') as f:
                    return f.read()

    except DownloadError as e:
        error_msg = str(e).lower()
        # Handle common error scenarios
        if "Requested format is not available" in error_msg:
            raise ValueError("⚠️ Requested format unavailable. Try a different video")
        elif "private video" in error_msg:
            raise ValueError("🔒 Private content or login required")
        elif "unable to download video data" in error_msg:
            raise ValueError("🚫 Video data inaccessible. May be age-restricted")
        elif "cookie" in error_msg:
            raise ValueError("Content requires cookies (not supported).")
        elif "too many requests" in error_msg:
            raise ValueError("Server error: Too many request. Try later or another video")

        logger.error("Error downloading video: %s", str(e), exc_info=True)
        raise ValueError(f"❌ Download failed: {error_msg.split(':')[-1].strip()}")
    except Exception as e:
        logger.error("Unexpected error on API video %s", str(e), exc_info=True)
        raise RuntimeError(f"🚨 Unexpected error: {str(e)}") from e
