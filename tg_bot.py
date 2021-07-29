import logging
import os

import redis
import telegram
from dotenv import load_dotenv
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from logs_handler import TelegramLogsHandler

logger = logging.getLogger('sale_bots logger')

_database = None


def start(update, context):
    update.message.reply_text(text='Привет!')
    return "ECHO"


def echo(update, context):
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'ECHO': echo
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    db.set(chat_id, next_state)


def get_database_connection():
    global _database
    if _database is None:
        redis_password = os.getenv("REDIS_DB_PASS")
        redis_host, redis_port = os.getenv('REDISLABS_ENDPOINT').split(':')
        _database = redis.Redis(host=redis_host, port=redis_port,
                                password=redis_password)
    return _database


def error_handler(update, context, tg_chat_id):
    logger.exception(msg='Exception while handling an update:')


def main():
    load_dotenv()
    tg_token = os.getenv('TG_BOT_TOKEN')
    tg_chat_id = os.getenv('TG_CHAT_ID')
    tg_bot = telegram.Bot(token=tg_token)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot, tg_chat_id))
    logger.info('ТГ бот запущен')

    updater = Updater(tg_token)
    dp = updater.dispatcher
    dp.add_handler(CallbackQueryHandler(handle_users_reply))
    dp.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dp.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()


if __name__ == '__main__':
    main()
