import logging
import os
import textwrap

import redis
import telegram
from dotenv import load_dotenv
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater

from logs_handler import TelegramLogsHandler
from moltin import get_all_products
from moltin import get_product

logger = logging.getLogger('sale_bots logger')

_database = None


def start(update, context):
    reply_markup = InlineKeyboardMarkup(create_keyboard(context))

    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def create_keyboard(context):
    all_products = get_all_products(context.bot_data['moltin_token'])
    keyboard = []
    for product in all_products['data']:
        keyboard.append([InlineKeyboardButton(product['name'],
                                             callback_data=product['id'])])
    return keyboard


def get_product_info(update, context):
    query = update.callback_query
    product = get_product(context.bot_data['moltin_token'], query.data)['data']
    text = f'''
            {product['name']}
            
            {product['meta']['display_price']['with_tax']['formatted']} per kg
            {product['meta']['stock']['level']}kg on stock
            
            {product['description']} from deep-deep ocean
            '''
    query.edit_message_text(text=textwrap.dedent(text))
    return "START"


def echo(update, context):
    users_reply = update.message.text
    update.message.reply_text(users_reply)
    return "ECHO"


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        print('update_message') #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        print('callback_query') #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        user_reply = update.callback_query.data
        print(user_reply) #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        chat_id = update.callback_query.message.chat_id
        print(chat_id) #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")
        print(user_state) #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    states_functions = {
        'START': start,
        'ECHO': echo,
        'HANDLE_MENU': get_product_info
    }
    state_handler = states_functions[user_state]
    next_state = state_handler(update, context)
    print(next_state) #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    db.set(chat_id, next_state)


def get_database_connection():
    global _database
    if _database is None:
        redis_password = os.getenv("REDIS_DB_PASS")
        redis_host, redis_port = os.getenv('REDISLABS_ENDPOINT').split(':')
        _database = redis.Redis(host=redis_host, port=redis_port,
                                password=redis_password)
    return _database


def error_handler(update, context):
    logger.exception(msg='Exception while handling an update:',
                     exc_info=context.error)


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
    dp.bot_data['moltin_token'] = os.getenv('ELASTICPATH_CLIENT_ID')
    dp.add_handler(CallbackQueryHandler(handle_users_reply))
    dp.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dp.add_handler(CommandHandler('start', handle_users_reply))
    dp.add_error_handler(error_handler)
    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
