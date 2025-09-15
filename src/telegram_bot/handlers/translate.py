import logging
import requests
from telebot.util import extract_command

from . import helper

logger = logging.getLogger(__name__)

def register_handlers(bot):
    @bot.message_handler(commands=["es_en", "en_es"])
    def translate_es_en(message):
        if not helper.is_valid_command(message): return
        
        user_text = helper.extract_arguments(message)
        if not user_text:
            return bot.reply_to(message, "Please, type a text to translate")

        command = str(extract_command(message.text))

        lang_pairs = {"tl_es_en": "es|en", "tl_en_es": "en|es"}
        lang = lang_pairs.get(command, "en|es")

        URL = f"https://api.mymemory.translated.net/get?q={user_text}&langpair={lang}"

        try:
            response = requests.get(URL)
            response.raise_for_status()

            text_info = response.json()
            text_tl = text_info["responseData"]["translatedText"]

            return bot.reply_to(message, text_tl)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return bot.reply_to(message, f"Translation failed. Error: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Error processing JSON: {e}")
            return bot.reply_to(
                message, "Translation failed. Could not process the response."
            )
