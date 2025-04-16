import os
from dotenv import load_dotenv
import telebot
import api_llm
from flask import Flask, request

# ========== Initial configuration ==========
app = Flask(__name__)
conversation_histories = {}  # Save the history
SYSTEM_MESSAGE = "You are a professional telegram bot to help people. Answer very briefly"

# ========== Bot config ==========
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME")
API_TOKEN = os.getenv("API_TOKEN")
API_URL = os.getenv("API_URL")
LLM_MODEL = os.getenv("LLM_MODEL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(BOT_TOKEN)

def use_get_api_llm(message, user_text, reset_history=False):
    try:
        bot.send_chat_action(message.chat.id, "typing")
        key = (message.chat.id, message.from_user.id)

        # Create unique key per chat-user
        if reset_history or key not in conversation_histories:
            conversation_histories[key] = [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": user_text}
            ]
        else:       
            # Add history only to private
            conversation_histories[key].append({"role": "user", "content": user_text})
            print(conversation_histories)
        # Get answer
        answer_api = api_llm.get_api_llm(conversation_histories[key], API_TOKEN, API_URL, LLM_MODEL)

        if not answer_api.get("error"):
            content = answer_api["choices"][0]["message"]["content"]
            conversation_histories[key].append({"role": "assistant", "content": content})
            bot.reply_to(message, content, parse_mode="markdown")
        else:
            error_msg = answer_api.get('error', {}).get('message', 'Error desconocido')
            print(error_msg)
            bot.reply_to(message, f"❌ Server error: {error_msg}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        bot.reply_to(message, "❌ Internal error. Try later.")

def setup_bot_handlers():
    #Bot ID to detect answer
    bot_user_id = bot.get_me().id 

    # Config commands
    bot.set_my_commands([
        telebot.types.BotCommand("/help", "Show all commands"),
        telebot.types.BotCommand("/ask", "Ask something"),
        telebot.types.BotCommand("/new", "Reload the conversation"),
    ])

    # Handler to /help
    @bot.message_handler(commands=["help", f"help@{BOT_NAME}"], chat_types=["private", "group", "supergroup"])
    def send_help(message):
        help_text = (
            "🤖 *Commands available:* \n\n"
            "/ask [questions] - init the conversation\n"
            "/new - Reload the conversation history\n"
            "/help - Show help"
        )
        bot.reply_to(message, help_text, parse_mode="markdown")

    # Handler to /new (clear history)
    @bot.message_handler(commands=["new", f"new@{BOT_NAME}"], chat_types=["private", "group", "supergroup"])
    def clear_history(message):
        key = (message.chat.id, message.from_user.id)
        if key in conversation_histories:
            del conversation_histories[key]
        bot.reply_to(message, "♻️ Conversation reloaded")

    # Handler to /ask in group
    @bot.message_handler(commands=["ask", f"ask@{BOT_NAME}"], chat_types=["private", "group", "supergroup"], content_types=["text"])
    def handle_ask_command_group(message):
        # Extract command
        command = message.text.split()[0].strip()
        # Extract question
        question = message.text.replace(command, "", 1).strip()

        if not question:
            return bot.reply_to(message, "❌ Use: /ask [your question]")
        use_get_api_llm(message, question, reset_history=True)
            
    # Handler to /ask in private
    @bot.message_handler(chat_types=["private"], content_types=["text"])
    def handle_ask_command_group(message):
        use_get_api_llm(message, message.text)

    # handler to answer to message's bot
    @bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.from_user.id == bot_user_id, chat_types=["private"], content_types=["text"])
    def handle_reply(message):
        use_get_api_llm(message, message.text)

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
        serve(app, host='0.0.0.0', port=8080)  # Using waitress on a hosting
    else:
        app.run(host='0.0.0.0', port=8080, debug=False)
