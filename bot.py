import os
from dotenv import load_dotenv
import telebot
import apideepseek

load_dotenv()

BOT_TOKEN = str(os.getenv("BOT_TOKEN"))
BOT_NAME  = str(os.getenv("BOT_NAME"))
API_KEY   = str(os.getenv("DEEP_SEEK_TOKEN"))
API_URL   = str(os.getenv("API_URL"))

bot = telebot.TeleBot(BOT_TOKEN)
bot.set_my_commands([
    telebot.types.BotCommand("/help", "Show all the commands"),
    telebot.types.BotCommand("/ask", "Ask anything you want to get information"),
])

@bot.message_handler(commands=["ask", f"ask@{BOT_NAME}"], chat_types=["private", "group", "supergroup"])
def chat_tanuk(message):
    bot.send_chat_action(message.chat.id, "typing")
    
    # return a json
    answer_api = apideepseek.getApiDeepSeek(message.text, API_KEY, API_URL)
    content = str()

    if not "error" in answer_api:
        # Parsing the information of the user input 
        content = answer_api["choices"][0]["message"]["content"]
    else:
        # In case of a problem with API
        print(answer_api["error"])
        content = "Request API failed. Try later"

    bot.reply_to(message, content, parse_mode="markdown")

@bot.message_handler(commands=["help", f"help@{BOT_NAME}"], chat_types=["private", "group","supergroup"])
def send_help(message):

    help_text = """
    Commands available
    /ask can ask
    """
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

bot.infinity_polling()
