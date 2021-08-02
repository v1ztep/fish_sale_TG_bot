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
from moltin import add_product_to_cart
from moltin import get_all_products
from moltin import get_image
from moltin import get_product

logger = logging.getLogger('sale_bots logger')

_database = None


def get_menu_keyboard(context):
    all_products = get_all_products(context.bot_data['moltin_token'])
    keyboard = []
    for product in all_products['data']:
        keyboard.append([InlineKeyboardButton(product['name'],
                                              callback_data=product['id'])])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def get_description_keyboard(product_id):
    keyboard = [[InlineKeyboardButton('1 кг', callback_data=f'{product_id} 1'),
                InlineKeyboardButton('5 кг', callback_data=f'{product_id} 5'),
                InlineKeyboardButton('10 кг', callback_data=f'{product_id} 10')],
                [InlineKeyboardButton("Назад", callback_data='to_menu')]
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def start(update, context):
    reply_markup = get_menu_keyboard(context)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def show_product_info(update, context):
    query = update.callback_query
    query.answer()
    product_id = query.data
    product = get_product(context.bot_data['moltin_token'], product_id)['data']
    image_id = product['relationships']['main_image']['data']['id']
    image = get_image(context.bot_data['moltin_token'], image_id)
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    text = f'''
            {product['name']}
            
            {product['meta']['display_price']['with_tax']['formatted']} per kg
            {product['meta']['stock']['level']}kg on stock
            
            {product['description']} from deep-deep ocean
            '''
    reply_markup = get_description_keyboard(product_id)
    context.bot.send_photo(chat_id=chat_id, photo=image,
                           caption=textwrap.dedent(text),
                           reply_markup=reply_markup)

    context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    return "HANDLE_DESCRIPTION"


def description_buttons(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if query.data == 'to_menu':
        reply_markup = get_menu_keyboard(context)
        context.bot.send_message(chat_id=chat_id, text='Please choose:',
                                 reply_markup=reply_markup)
        context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return "HANDLE_MENU"

    product_id, quantity = query.data.split()
    add_product_to_cart(moltin_token=context.bot_data['moltin_token'],
                        cart_id=chat_id,
                        product_id=product_id,
                        quantity=int(quantity))
    return "HANDLE_DESCRIPTION"


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
        'HANDLE_MENU': show_product_info,
        'HANDLE_DESCRIPTION': description_buttons
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
