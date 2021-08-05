import textwrap

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from moltin import get_all_products


def get_menu_keyboard(context):
    all_products = get_all_products(context.bot_data['moltin_token'])
    keyboard = []
    for product in all_products['data']:
        keyboard.append([InlineKeyboardButton(product['name'],
                                              callback_data=product['id'])])
    keyboard.append([InlineKeyboardButton("Корзина", callback_data='to_cart')])
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


def get_description_keyboard(product_id):
    keyboard = [[InlineKeyboardButton('1 кг', callback_data=f'{product_id} 1'),
                InlineKeyboardButton('5 кг', callback_data=f'{product_id} 5'),
                InlineKeyboardButton('10 кг', callback_data=f'{product_id} 10')],
                [InlineKeyboardButton("Корзина", callback_data='to_cart')],
                [InlineKeyboardButton("В меню", callback_data='to_menu')]
                ]
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
