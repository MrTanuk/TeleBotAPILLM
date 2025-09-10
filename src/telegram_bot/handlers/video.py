import logging
import telebot

from .. import config
from ..services import video_api
from . import helper

logger = logging.getLogger(__name__)

def register_handlers(bot):
    @bot.message_handler(commands=["dl"])
    def send_video(message):
        if not helper.is_valid_command(message): return
        try:
            args = helper.extract_arguments(message)
            if not args:
                raise IndexError
            url = args.split()[0].strip()
            
            bot.send_chat_action(message.chat.id, 'upload_video')
            video = video_api.download_video(url)
            
            config.bot.send_video(
                chat_id=message.chat.id,
                video=video,
                reply_to_message_id=message.message_id,
                supports_streaming=True,
                timeout=120
            )
        except IndexError:
            bot.reply_to(message, "Please provide a URL after the command.\nExample: `/dl https://...`")
        except (ValueError, RuntimeError, Exception) as e:
            logger.error(f"Failed to process /dl command: {e}", exc_info=True)
            bot.reply_to(message, str(e))
