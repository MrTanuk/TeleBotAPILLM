import logging

from ..handlers.ai import use_get_api_llm
from ..services.speech_to_text import speech

logger = logging.getLogger(__name__)

def register_handlers(bot):
    @bot.message_handler(content_types=["voice"])
    def speech_voice(message):
        try:
            # Get audio file information
            audio_id = message.voice.file_id
            audio_info = bot.get_file(audio_id)

            # Download the file directly to memory
            ogg_bytes = bot.download_file(audio_info.file_path)

            # Perform the transcription
            text = speech(ogg_bytes)
            use_get_api_llm(bot, message, text)

        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            bot.reply_to(message, "An error occurred while processing the audio")
