import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

EP_ACCESS_TOKEN = None
EP_TOKEN_LIFETIME = None


def get_ep_access_token(moltin_token):
    now_time = time.time()
    global EP_ACCESS_TOKEN
    global EP_TOKEN_LIFETIME

    if not EP_TOKEN_LIFETIME or EP_TOKEN_LIFETIME < now_time:
        EP_ACCESS_TOKEN, EP_TOKEN_LIFETIME = create_ep_access_token(moltin_token)

    return EP_ACCESS_TOKEN


def create_ep_access_token(moltin_token):
    url = 'https://api.moltin.com/oauth/access_token'
    data = {
        'client_id': f'{moltin_token}',
        'grant_type': 'implicit'
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    response_info = response.json()
    ep_token_lifetime = response_info['expires']
    ep_access_token = response_info['access_token']
    return ep_access_token, ep_token_lifetime


def get_all_products(moltin_token):
    access_token = get_ep_access_token(moltin_token)
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/products',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def get_product(moltin_token, product_id):
    access_token = get_ep_access_token(moltin_token)
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def get_image(moltin_token, image_id):
    access_token = get_ep_access_token(moltin_token)
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/files/{image_id}',
                            headers=headers)
    response.raise_for_status()
    image = response.json()['data']['link']['href']
    return image


def add_product_to_cart(moltin_token, cart_id):
    cart_tg_id = f'tg{cart_id}' #<<<<<<<<убрать строку, передать готовый уникальный ID<<<<<<<<<<<<
    url = f'https://api.moltin.com/v2/carts/{cart_tg_id}/items'
    access_token = get_ep_access_token(moltin_token)
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    data = {"data":
                 { "sku": "2",
                   "type": "cart_item",
                   "quantity": 1}
             }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


def get_cart(moltin_token, cart_id):
    cart_tg_id = f'tg{cart_id}'  # <<<<<<<<убрать строку, передать готовый уникальный ID<<<<<<
    access_token = get_ep_access_token(moltin_token)
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{cart_tg_id}',
                            headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart_items(moltin_token, cart_id):
    cart_tg_id = f'tg{cart_id}'  # <<<<<<<<убрать строку, передать готовый уникальный ID<<<<<<<<<<<<
    url = f'https://api.moltin.com/v2/carts/{cart_tg_id}/items'
    access_token = get_ep_access_token(moltin_token)
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    moltin_token = os.getenv('ELASTICPATH_CLIENT_ID')
    tg_chat_id = os.getenv('TG_CHAT_ID')

    all_products = get_all_products(moltin_token)
    add_product = add_product_to_cart(moltin_token, tg_chat_id)
    cart = get_cart(moltin_token, tg_chat_id)
    items = get_cart_items(moltin_token, tg_chat_id)
    get_product_info = get_product(moltin_token, )
    image = get_image(moltin_token, )

    with open('response.json', "w", encoding='utf8') as file:
        json.dump(get_product_info, file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main()
