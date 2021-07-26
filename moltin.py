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
    data = {
        'client_id': f'{moltin_token}',
        'grant_type': 'implicit'
    }
    response = requests.post('https://api.moltin.com/oauth/access_token',
                             data=data)
    response_info = response.json()
    ep_token_lifetime = response_info['expires']
    ep_access_token = response_info['access_token']
    return ep_access_token, ep_token_lifetime


def main():
    moltin_token = os.getenv('ELASTICPATH_CLIENT_ID')
    access_token = get_ep_access_token(moltin_token)

    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/products',
                            headers=headers)


    print(response.json())
    with open('response.json', "w", encoding='utf8') as file:
        json.dump(response.json(), file, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main()
