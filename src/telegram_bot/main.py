import os
import logging
from flask import Flask, request
import telebot
from . import config
from .handlers import general, ai, video

# ========== Initial App Setup ==========
app = Flask(__name__)

def setup_bot_handlers():
    """Import and register all handlers of their correctly dirs"""
    general.register_handlers(config.bot)
    ai.register_handlers(config.bot)
    video.register_handlers(config.bot)

# ========== Flask Routes for Webhook ==========
@app.route('/')
def health_check():
    return "🤖 Bot is active.", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        config.bot.process_new_updates([update])
        return '', 200
    return 'Invalid content type', 403

# ========== Application Entry Point ==========
if __name__ == '__main__':
    # Setup logging first
    config.setup_logging()

    logger = logging.getLogger(__name__)
    # Then setup bot handlers
    setup_bot_handlers()
    
    if os.environ.get('HOSTING') == "production":
        from waitress import serve
        logger.info(f"Starting in production mode, setting webhook to {config.WEBHOOK_URL}")
        config.bot.remove_webhook()
        config.bot.set_webhook(url=config.WEBHOOK_URL + '/webhook')
        serve(app, host='0.0.0.0', port=8080)
    else:
        logger.info("Starting in development mode with polling...")
        config.bot.delete_webhook()
        config.bot.infinity_polling()
