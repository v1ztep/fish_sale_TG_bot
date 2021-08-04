import logging
import os
import re
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
from moltin import create_customer
from moltin import get_all_products
from moltin import get_cart_items
from moltin import get_image
from moltin import get_product
from moltin import remove_item_in_cart

logger = logging.getLogger('sale_bots logger')

_database = None


def get_menu_keyboard(context):
    all_products = get_all_products(context.bot_data['moltin_token'])
    keyboard = []
    for product in all_products['data']:
        keyboard.append([InlineKeyboardButton(product['name'],
                                              callback_data=product['id'])])
    keyboard.append([InlineKeyboardButton("Корзина", callback_data='to_cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def get_description_keyboard(product_id):
    keyboard = [[InlineKeyboardButton('1 кг', callback_data=f'{product_id} 1'),
                InlineKeyboardButton('5 кг', callback_data=f'{product_id} 5'),
                InlineKeyboardButton('10 кг', callback_data=f'{product_id} 10')],
                [InlineKeyboardButton("Корзина", callback_data='to_cart')],
                [InlineKeyboardButton("В меню", callback_data='to_menu')]
                ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def get_description_text(product):
    text = f'''
        {product['name']}

        {product['meta']['display_price']['with_tax']['formatted']} per kg
        {product['meta']['stock']['level']}kg on stock

        {product['description']} fish from deep-deep ocean
        '''
    return textwrap.dedent(text)


def get_cart_keyboard(cart_items):
    keyboard = []
    for product in cart_items['data']:
        keyboard.append([InlineKeyboardButton(f"Убрать из корзины {product['name']}",
                                              callback_data=product['id'])])
    if keyboard:
        keyboard.append(
            [InlineKeyboardButton('Оплата', callback_data='to_payment')])
    keyboard.append([InlineKeyboardButton('В меню', callback_data='to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def get_cart_text(cart_items):
    text = ''
    for product in cart_items['data']:
        text += f'''
            {product['name']}
            {product['description']} fish from deep-deep ocean
            {product['meta']['display_price']['with_tax']['unit']['formatted']} per kg
            {product['quantity']}kg in cart for {product['meta']['display_price']
            ['with_tax']['value']['formatted']} 
            '''
    text += f'''
            Total: {cart_items['meta']['display_price']['with_tax']['formatted']}
            '''
    return textwrap.dedent(text)


def show_menu(context, chat_id, message_id):
    menu_keyboard = get_menu_keyboard(context)
    context.bot.send_message(chat_id=chat_id, text='Please choose:',
                             reply_markup=menu_keyboard)
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


def show_cart(context, chat_id, message_id):
    cart_items = get_cart_items(context.bot_data['moltin_token'], chat_id)
    cart_text = get_cart_text(cart_items)
    cart_keyboard = get_cart_keyboard(cart_items)
    context.bot.send_message(chat_id=chat_id,
                             text=cart_text,
                             reply_markup=cart_keyboard)
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)


def start(update, context):
    reply_markup = get_menu_keyboard(context)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return 'HANDLE_MENU'


def menu_handler(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    if query.data == 'to_cart':
        show_cart(context, chat_id, message_id)
        return 'HANDLE_CART'

    product_id = query.data
    product = get_product(context.bot_data['moltin_token'], product_id)['data']
    image_id = product['relationships']['main_image']['data']['id']
    image = get_image(context.bot_data['moltin_token'], image_id)

    description_text = get_description_text(product)
    description_keyboard = get_description_keyboard(product_id)
    context.bot.send_photo(chat_id=chat_id, photo=image,
                           caption=description_text,
                           reply_markup=description_keyboard)
    context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    return 'HANDLE_DESCRIPTION'


def description_handler(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if query.data == 'to_menu':
        show_menu(context, chat_id, message_id)
        return 'HANDLE_MENU'
    elif query.data == 'to_cart':
        show_cart(context, chat_id, message_id)
        return 'HANDLE_CART'

    product_id, quantity = query.data.split()
    add_product_to_cart(moltin_token=context.bot_data['moltin_token'],
                        cart_id=chat_id,
                        product_id=product_id,
                        quantity=int(quantity))
    query.answer(text=f'+{quantity}кг добавлены в корзину')
    return 'HANDLE_DESCRIPTION'


def cart_handler(update, context):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if query.data == 'to_menu':
        show_menu(context, chat_id, message_id)
        return 'HANDLE_MENU'
    if query.data == 'to_payment':
        context.bot.edit_message_text(chat_id=chat_id,
                                      text='Пришлите, пожалуйста, ваш email',
                                      message_id=message_id)
        return 'WAITING_EMAIL'

    cart_item_id = query.data
    remaining_items = remove_item_in_cart(context.bot_data['moltin_token'],
                                          chat_id, cart_item_id)
    cart_text = get_cart_text(remaining_items)
    cart_keyboard = get_cart_keyboard(remaining_items)
    context.bot.edit_message_text(chat_id=chat_id,
                                  text=cart_text,
                                  reply_markup=cart_keyboard,
                                  message_id=message_id)
    return 'HANDLE_CART'


def email_handler(update, context):
    validate_email_re = r"[^@]+@[^@]+\.[^@]+"
    users_reply = update.message.text
    if not re.fullmatch(validate_email_re, users_reply):
        text = f'''
                Кажется вы неправильно ввели почту: {users_reply}
                Пришлите ещё раз.
                '''
        update.message.reply_text(text=textwrap.dedent(text))
        return 'WAITING_EMAIL'
    chat_id = update.message.chat_id
    cart_items = get_cart_items(context.bot_data['moltin_token'], chat_id)
    cart_text = get_cart_text(cart_items)
    text = f'''
        Мы свяжемся с вами по почте: {users_reply}, для подтверждения вашего заказа:
        {cart_text}
        '''
    update.message.reply_text(text=textwrap.dedent(text))
    customer_name = f'{update.message.chat.first_name} {update.message.chat.last_name}'
    create_customer(context.bot_data['moltin_token'], customer_name, users_reply)
    return 'START'


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
    user_state = db.get(chat_id).decode("utf-8")
    if user_reply == '/start':
        user_state = 'START'
    elif update.message and user_state != 'WAITING_EMAIL':
        return

    states_functions = {
        'START': start,
        'HANDLE_MENU': menu_handler,
        'HANDLE_DESCRIPTION': description_handler,
        'HANDLE_CART': cart_handler,
        'WAITING_EMAIL': email_handler
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
