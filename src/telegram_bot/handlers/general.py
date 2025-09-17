import logging
import telebot

from .. import config
from . import helper

logger = logging.getLogger(__name__)

def register_handlers(bot):
    """Sets up all the message handlers for the bot."""
    # Decorators now use the `config.bot` instance
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Greet the bot"),
        telebot.types.BotCommand("/help", "Show all commands"),
        telebot.types.BotCommand("/ask", "Ask a question"),
        telebot.types.BotCommand("/clear", "Clear conversation history"),
        telebot.types.BotCommand("/dl", "Download a video"),
        telebot.types.BotCommand("/es_en", "Translate text from spanish to english"),
        telebot.types.BotCommand("/en_es", "Translate text from english to spanish")
    ])

    @bot.message_handler(commands=["start", "help"])
    def send_start_help(message):
        if not helper.is_valid_command(message): return
        help_text = (
            "Send voice message to ask AI and get a respond (only in private)\n\n"
            "🤖 **Available Commands:**\n\n"
            "/start - Greet the bot\n"
            "/help - Show this help message\n"
            "/ask `[question]` - Start or continue a conversation\n"
            "/clear - Clear the conversation history\n"
            "/en\_es - Type to translte from english to spanish\n"
            "/es\_en - Type to translte from spanish to english\n"
            "/dl `[url]` - Download a video from:\n"
            "**Youtube**\n"
            "**Instagram**\n"
            "**Facebook**\n"
            "**TikTok**\n\n"
            f"In groups, commands must be addressed to me (e.g., `/ask@{config.BOT_NAME}`)."
        )
        bot.reply_to(message, help_text, parse_mode="markdown")


    @bot.message_handler(content_types=['new_chat_members'])
    def handle_new_users(message):
        for new_user in message.new_chat_members:
            bot.send_message(message.chat.id, f'Welcome, {new_user.first_name}! I hope you enjoy this group 🎉.')
