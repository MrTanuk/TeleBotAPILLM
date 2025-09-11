import logging
from datetime import datetime, timedelta, timezone
import telebot

from .. import config
from ..services import llm_api

from . import helper

logger = logging.getLogger(__name__)
response_history = {}

def register_handlers(bot):
    @bot.message_handler(commands=["clear"])
    def clear_history(message):
        if not helper.is_valid_command(message): return
        key = (message.chat.id, message.from_user.id)
        if key in response_history:
            del response_history[key]
        bot.reply_to(message, "♻️ Conversation history has been cleared.")

    # Handler for /ask command (works in all chat types)
    @bot.message_handler(commands=["ask"])
    def handle_ask(message):
        if not helper.is_valid_command(message): return
        question = helper.extract_arguments(message)
        if not question:
            bot.reply_to(message, "Please ask a question after the `/ask` command.")
            return
        is_group = message.chat.type in ["group", "supergroup"]
        use_get_api_llm(bot, message, question, is_group=is_group)

    # Handler for direct messages in private chat (no command needed)
    @bot.message_handler(chat_types=["private"], content_types=["text"], func=lambda msg: not msg.text.startswith('/'))
    def handle_private_text(message):
        use_get_api_llm(bot, message, message.text, is_group=False)

# --- Core Logic Functions ---
def use_get_api_llm(bot, message, user_text, is_group=False):
    """Handles the logic of sending a prompt to the LLM and replying to the user."""
    try:
        # In groups, ignore messages that are not explicit commands or replies to the bot
        if is_group and message.reply_to_message is None:
            if not helper.is_valid_command(message):
                return
        
        bot.send_chat_action(message.chat.id, "typing")
        user_key = (message.chat.id, message.from_user.id)
        current_time = datetime.now(timezone.utc)
        
        # Check if history exists and needs reset
        history_data = response_history.get(user_key)
        if history_data and (current_time - history_data['last_active'] > timedelta(hours=1)):
            response_history.pop(user_key, None)
            history_data = None # Force re-initialization
            bot.send_message(message.chat.id, "🕒 Chat history has been reset due to 1 hour of inactivity.")
        
        # Initialize new user history if needed
        if not history_data:
            response_history[user_key] = {
                'conversation': [{"role": "system", "content": config.SYSTEM_MESSAGE}],
                'last_active': current_time
            }

        # Update last activity timestamp and add new message
        response_history[user_key]['last_active'] = current_time
        response_history[user_key]['conversation'].append({"role": "user", "content": user_text})

        # Maintain conversation history limit
        MAX_HISTORY = 25
        response_history[user_key]['conversation'] = response_history[user_key]['conversation'][-MAX_HISTORY:]

        # Generate AI response using current conversation context
        ai_response = llm_api.get_api_llm(
            response_history[user_key]['conversation'],
            config.API_TOKEN,
            config.API_URL,
            config.LLM_MODEL,
            config.PROVIDER,
            config.MAX_OUTPUT_TOKENS
        )
        
        # Send response and update history
        return bot.reply_to(message, ai_response, parse_mode="markdown")
        response_history[user_key]['conversation'].append({"role": "assistant", "content": ai_response})

    except (KeyError, ValueError, ConnectionError, RuntimeError) as e:
        return bot.reply_to(message, str(e))
    except telebot.apihelper.ApiTelegramException as e:
        if "Can't find end of the entity starting" in str(e):
            return bot.reply_to(message, ai_response) # Send as plain text if markdown fails
        logger.error("Telegram API Error: %s", e)
    except Exception as e:
        logger.error("Unexpected error in use_get_api_llm: %s", e, exc_info=True)
        return bot.reply_to(message, "🚨 An unexpected error occurred. Please try again.")
