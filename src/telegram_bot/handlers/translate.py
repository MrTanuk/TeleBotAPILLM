import logging
import telebot

from ..services import llm_api
from .. import config
from . import helper

logger = logging.getLogger(__name__)


def register_handlers(bot):
    @bot.message_handler(commands=["es_en", "en_es"])
    def translate_es_en(message):
        try:
            if not helper.is_valid_command(message):
                return

            user_text = helper.extract_arguments(message)
            if not user_text:
                return bot.reply_to(message, "Please, type a text to translate")

            command = str(telebot.util.extract_command(message.text))

            lang_pairs = {"es_en": "Spanish to English", "en_es": "English to Spanish"}
            lang = lang_pairs.get(command, "English to Spanish")

            prompt = f"Translate the following text from {lang}: {user_text}"

            messages_payload = [
                {"role": "system", "content": "You are a professional translator. Respond only with the translated text and nothing else."},
                {"role": "user", "content": prompt}
            ]
            

            ai_response = llm_api.get_api_llm(
                messages_payload,
                config.API_TOKEN,
                config.API_URL,
                config.LLM_MODEL,
                config.PROVIDER,
                800,
            )
            return bot.reply_to(message, ai_response, parse_mode="markdown")

        except (KeyError, ValueError, ConnectionError, RuntimeError) as e:
            return bot.reply_to(message, str(e))
        except telebot.apihelper.ApiTelegramException as e:
            if "Can't find end of the entity starting" in str(e):
                return bot.reply_to(message, ai_response) # Send as plain text if markdown fails
            logger.error("Telegram API Error: %s", e)
        except Exception as e:
            logger.error("Unexpected error in use_get_api_llm: %s", e, exc_info=True)
            return bot.reply_to(message, "🚨 An unexpected error occurred. Please try again.")
