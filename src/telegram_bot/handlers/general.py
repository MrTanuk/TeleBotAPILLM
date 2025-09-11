import logging
import telebot

from .. import config
from . import helper

def register_handlers(bot):
    """Sets up all the message handlers for the bot."""
    # Decorators now use the `config.bot` instance
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Greet the bot"),
        telebot.types.BotCommand("/help", "Show all commands"),
        telebot.types.BotCommand("/ask", "Ask a question"),
        telebot.types.BotCommand("/clear", "Clear conversation history"),
        telebot.types.BotCommand("/dl", "Download a video")
    ])

    @bot.message_handler(commands=["start"])
    def send_start(message):
        if not helper.is_valid_command(message): return
        config.bot.reply_to(message, "Welcome to Mario Kart")

    @bot.message_handler(commands=["help"])
    def send_help(message):
        if not helper.is_valid_command(message): return
        help_text = (
            "🤖 **Available Commands:**\n\n"
            "/start - Greet the bot\n"
            "/help - Show this help message\n"
            "/ask `[question]` - Start or continue a conversation\n"
            "/clear - Clear the conversation history\n"
            "/dl `[url]` - Download a video from:\n"
            "**Youtube**\n"
            "**Instagram**\n"
            "**Facebook**\n"
            "**TikTok**\n\n"
            f"In groups, commands must be addressed to me (e.g., `/ask@{config.BOT_NAME}`)."
        )
        config.bot.reply_to(message, help_text, parse_mode="markdown")


    @bot.message_handler(content_types=['new_chat_members'])
    def handle_new_users(message):
        for new_user in message.new_chat_members:
            config.bot.send_message(message.chat.id, f'Welcome, {new_user.first_name}! I hope you enjoy this group 🎉.')
