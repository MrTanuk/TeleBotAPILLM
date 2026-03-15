import logging
import os
import re
import shutil

from telegram import Update, constants
from telegram.ext import ContextTypes

from ..services import video_api

logger = logging.getLogger(__name__)


async def dl_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /dl command, extracting URL from arguments or replies."""
    if not update.message or not update.effective_chat:
        return

    url: str | None = None

    if context.args:
        url = context.args[0]
    elif update.message.reply_to_message:
        original_msg = update.message.reply_to_message
        text_to_check = original_msg.text or original_msg.caption or ""

        found_urls = re.findall(r"(https?://[^\s]+)", text_to_check)
        if found_urls:
            url = found_urls[0]

    if not url:
        await update.message.reply_text(
            "No link found. Use `/dl [url]` or reply to a message containing a link."
        )
        return

    chat_id = update.effective_chat.id

    status_msg = await update.message.reply_text(
        "⏳ Processing video... (this may take a few seconds)"
    )
    await context.bot.send_chat_action(
        chat_id=chat_id, action=constants.ChatAction.UPLOAD_VIDEO
    )

    video_path: str | None = None
    try:
        video_path = await video_api.download_video(url)

        file_size = os.path.getsize(video_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            await status_msg.edit_text(
                "❌ The video is too large to send via Telegram (>50MB)."
            )
            return

        await update.message.reply_video(
            video=open(video_path, "rb"),
            caption="🎥 Here is your video",
            supports_streaming=True,
            read_timeout=120,
            write_timeout=120,
        )

        await status_msg.delete()

    except ValueError as e:
        await status_msg.edit_text(f"⚠️ {str(e)}")
    except Exception as e:
        logger.error("Download error: %s", e, exc_info=True)
        await status_msg.edit_text(
            "🚨 Download failed. Please check if the link is public and valid."
        )

    finally:
        if video_path and os.path.exists(video_path):
            try:
                folder = os.path.dirname(video_path)
                shutil.rmtree(folder, ignore_errors=True)
            except OSError:
                pass
