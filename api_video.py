import os
import re
import tempfile
from yt_dlp import YoutubeDL
from yt_dlp import DownloadError

def download_video(url):
    # Allowed domain validation
    pattern = (
    r'^(https?://)?(?:www\.)?'
    r'(?:'
    r'(?:youtube\.com/|youtu\.be/)(?:watch\?v=|shorts/)|'  # YouTube (videos and shorts)
    r'(?:facebook\.com|fb\.watch)/(?:reel/|watch/|reels/|videos/|share/)|'  # Facebook/Reels
    r'(?:instagram\.com|instagr\.am)/(?:reel/|reels/|p/)'  # Instagram/Reels videos
    r')'
    r'[\w\-]+/?[\w\-?=&]*$')
    if not re.match(pattern, url, re.IGNORECASE):
        raise IndexError("❌ URL not allowed. Only YouTube, Facebook, and Instagram video links are permitted")
    
    MAX_SIZE_MB = 45
    MAX_SIZE_BYTES = MAX_SIZE_MB * 1_000_000  # 45MB

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ydl_opts = {
                'outtmpl': f'{tmpdir}/%(id)s.%(ext)s',
                'format': 'bestvideo[ext=mp4][vcodec^=avc1]+bestaudio/best[height<=720]',
                'quiet': True,
                'no_warnings': False,
                'noplaylist': True,
                'max_filesize': MAX_SIZE_BYTES,  # 45MB
                'merge_output_format': 'mp4',
                'retries': 3,
                'fragment_retries': 3,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                },
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                    'when': 'post_process'
                }]
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info_dict)

                file_size = os.path.getsize(filename)
                if file_size > MAX_SIZE_BYTES:
                    raise ValueError(
                        f"❌ Video too large ({file_size/1_000_000:.2f}MB)\n"
                        f"(Limit: {MAX_SIZE_MB}MB)"
                    )

                with open(filename, 'rb') as f:
                    video_data = f.read()

        return video_data

    except IndexError as e:
        raise IndexError(str(e))
    except ValueError as e:
        raise ValueError(str(e))
    except DownloadError as e:
        error_msg = str(e)
        if "File is larger than max-filesize" in error_msg:
            raise ValueError(
                f"❌ The video exceeds the limit of... {MAX_SIZE_MB}MB. "
                "Try a shorter video."
            )
        elif "Video unavailable" in error_msg:
            raise ValueError("The video doesn't exit or is private")
        elif "accessible in your browser without being logged-in" in error_msg:
            raise ValueError("This content is private or requires authentication.")
        elif "There is no video in this post" in error_msg:
            raise ValueError("Send link that contains only video")
        raise ValueError(f"❌ Error downloading: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"🚨 Unexpected error during download: {str(e)}") from e
