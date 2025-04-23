from logging import error
import os
from dotenv import load_dotenv
from flask import Flask, request
import telebot
import api_llm

# ========== Initial configuration ==========
app = Flask(__name__)
SYSTEM_MESSAGE = "You are a professional telegram bot to help people. Answer briefly"

# ========== Bot config ==========
load_dotenv()

PROVIDER = "google"

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
API_TOKEN = os.getenv("API_TOKEN")
LLM_MODEL = os.getenv("LLM_MODEL")
if PROVIDER != "google":
    API_URL = os.getenv("API_URL")
else:
    API_URL = f"{os.getenv('API_URL')}/{str(LLM_MODEL)}:generateContent?key={str(API_TOKEN)}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(str(BOT_TOKEN))

def use_get_api_llm(message, user_text):
    try:
        bot.send_chat_action(message.chat.id, "typing")
        
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_text}
        ]
        MAX_OUTPUT_TOKENS = 1024

        # Get answer
        answer_api = api_llm.get_api_llm(messages, API_TOKEN, API_URL, LLM_MODEL, MAX_OUTPUT_TOKENS, PROVIDER)

        # Get only a string, it's the answer
        if not isinstance(answer_api, dict):
            bot.reply_to(message, answer_api, parse_mode="markdown")
        else:
            # Get a dict if there was a problem
            error_msg = answer_api.get("error")
            print(error_msg)
            bot.reply_to(message, f"❌ Server error. Try later")

    except telebot.apihelper.ApiTelegramException as e:
        # Respond without markdown in case there was problem with some 
        if "Can't find end of the entity starting" in str(e):
            print(e)
            bot.reply_to(message, answer_api)
        else:
            raise e

    except Exception as e:
        print(f"error: {str(e)}")
        bot.reply_to(message, "❌ Internal error. Try again.")

def setup_bot_handlers():
    # Config commands
    bot.set_my_commands([
        telebot.types.BotCommand("/help", "Show all commands"),
        telebot.types.BotCommand("/ask", "Ask something"),
    ])

    # Handler to /help
    @bot.message_handler(commands=["help", f"help@{BOT_NAME}"], chat_types=["private", "group", "supergroup"])
    def send_help(message):
        help_text = (
            "🤖 *Commands available:* \n\n"
            "/ask [questions] - init the conversation\n"
            "/help - Show help"
        )
        bot.reply_to(message, help_text, parse_mode="markdown")

    # Handler to /ask in group, private
    @bot.message_handler(commands=["ask", f"ask@{BOT_NAME}"], chat_types=[ "group", "supergroup"], content_types=["text"])
    @bot.message_handler(chat_types=["private"], content_types=["text"])
    def handle_all_question(message):

        if message.text.startswith('/'):
            # Extract command
            command = message.text.split()[0].strip()
            # Extract question
            question = message.text.replace(command, "", 1).strip()
        else:
            question = message.text.strip()

        if not question:
             return bot.reply_to(message, "❌ Use: /ask [your question]")

        use_get_api_llm(message, question)

# handlers config
setup_bot_handlers()

# ========== Flask routes ==========
@app.route('/')
def health_check():
    return "🤖 Bot active", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Invalid content type', 403

# ========== Entry point =========

if __name__ == '__main__':
    if os.environ.get('HOSTING'):
        from waitress import serve
        bot.remove_webhook()
        bot.set_webhook(url=WEBHOOK_URL + '/webhook')
        serve(app, host='0.0.0.0', port=8080)
    else:
        bot.delete_webhook()
        bot.infinity_polling()
        app.run(host='0.0.0.0', port=8080, debug=False)
