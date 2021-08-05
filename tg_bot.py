import logging
import os
import textwrap

import telegram
from dotenv import load_dotenv
from telegram.ext import CallbackQueryHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import MessageHandler
from telegram.ext import Updater
from validate_email import validate_email

from connect_to_redis_db import get_database_connection
from logs_handler import TelegramLogsHandler
from moltin import add_product_to_cart
from moltin import create_customer
from moltin import get_cart_items
from moltin import get_image
from moltin import get_product
from moltin import remove_item_in_cart
from fish_contents import get_cart_keyboard
from fish_contents import get_cart_text
from fish_contents import get_description_keyboard
from fish_contents import get_description_text
from fish_contents import get_menu_keyboard

logger = logging.getLogger('sale_bots logger')


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
    users_reply = update.message.text
    if not validate_email(email_address=users_reply, check_format=True,
                    check_blacklist=False, check_dns=False, check_smtp=False):
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
    if user_reply == '/start':
        user_state = 'START'
    elif update.message and db.get(chat_id).decode("utf-8") != 'WAITING_EMAIL':
        return
    else:
        user_state = db.get(chat_id).decode("utf-8")

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
