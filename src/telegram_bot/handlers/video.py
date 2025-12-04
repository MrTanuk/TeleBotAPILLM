import os
import asyncio
import logging
import shutil
from telegram import Update, constants
from telegram.ext import ContextTypes

from ..services import video_api

logger = logging.getLogger(__name__)

async def dl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /dl command, extracting URL from arguments or replies."""
    
    url = None

    # 1. Priority: Did the user write the URL with the command? (/dl https://...)
    if context.args:
        url = context.args[0]
    
    # 2. Secondary: Is it a reply to another message?
    elif update.message.reply_to_message:
        original_msg = update.message.reply_to_message
        text_to_check = original_msg.text or original_msg.caption or ""
        
        # Look for the first "word" that looks like a URL
        import re
        # Simple regex to find http/https
        found_urls = re.findall(r'(https?://[^\s]+)', text_to_check)
        if found_urls:
            url = found_urls[0]

    # 3. Validation
    if not url:
        await update.message.reply_text("No link found. Use `/dl [url]` or reply to a message containing a link.")
        return

    chat_id = update.effective_chat.id
    
    # Initial feedback
    status_msg = await update.message.reply_text("⏳ Processing video... (this may take a few seconds)")
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.UPLOAD_VIDEO)

    video_path = None
    try:
        # 2. EXECUTE IN SEPARATE THREAD (Concurrency Magic)
        # This frees the bot to continue responding to others while downloading
        video_path = await asyncio.to_thread(video_api.download_video, url)

        # 3. Check size (Telegram has strict limits for bots)
        file_size = os.path.getsize(video_path)
        if file_size > 50 * 1024 * 1024: # 50MB
            await status_msg.edit_text("❌ The video is too large to send via Telegram (>50MB).")
            return

        # 4. Send Video
        # open(video_path, 'rb') opens the file for binary reading
        await update.message.reply_video(
            video=open(video_path, 'rb'),
            caption=f"🎥 Here is your video",
            supports_streaming=True,
            read_timeout=120, 
            write_timeout=120
        )
        
        # Delete "Processing..." message
        await status_msg.delete()

    except ValueError as e:
        await status_msg.edit_text(f"⚠️ {str(e)}")
    except Exception as e:
        logger.error("Download error: %s", e, exc_info=True)
        await status_msg.edit_text("🚨 Download failed. Please check if the link is public and valid.")
    
    finally:
        # 5. MANDATORY CLEANUP
        # video_api creates a temp folder, we must delete it or the file
        if video_path and os.path.exists(video_path):
            try:
                # Delete the container folder created by mkdtemp in the service
                folder = os.path.dirname(video_path)
                shutil.rmtree(folder, ignore_errors=True)
            except OSError:
                pass
