# Чатбот магазин [Telegram](https://telegram.org/) интегрированный с CMS [Moltin](https://www.elasticpath.com/)

Чатбот для [Telegram](https://telegram.org/) с возможностью выбирать, добавлять и
удалять товар в корзине, оформлять покупку через [CMS Moltin](https://www.elasticpath.com/)

![gif](media/sale_bot.gif)

[Наглядная демонстрация с возможностью самому написать боту](#демонстрация)

## Настройки

* Необходимо зарегистрироваться в [Redislabs](https://redislabs.com/) - забрать 
адрес базы данных вида `redis-13965.f18.us-east-4-9.wc1.cloud.redislabs.com:16635` 
и его пароль.
* Создать бота в Telegram через специального бота:
[@BotFather](https://telegram.me/BotFather), забрать API ключ и написать 
созданному боту.
* Забрать свой `chat_id` через [@userinfobot](https://telegram.me/userinfobot) - 
  необходим для получения логов (ошибки будут идти именно этому пользователю).
* Зарегистрироваться в CMS [Moltin](https://www.elasticpath.com/), забрать 
`Client ID`. Заполнить товары в 
[CMS](https://dashboard.elasticpath.com/app/catalog/products).

### Переменные окружения

Создайте файл `.env` в корневой папке с кодом и запишите туда:
```
REDISLABS_ENDPOINT=АДРЕС_БД
REDIS_DB_PASS=ПАРОЛЬ_ВАШЕЙ_БД
TG_BOT_TOKEN=ВАШ_TELEGRAM_API_КЛЮЧ
TG_CHAT_ID=ВАШ_CHAT_ID
ELASTICPATH_CLIENT_ID=ВАШ_API_КЛЮЧ_MOLTIN
```


## Запуск

Для запуска у вас уже должен быть установлен [Python 3](https://www.python.org/downloads/release/python-379/).

- Скачайте код.
- Установите зависимости командой:
```
pip install -r requirements.txt
```
- Запустите скрипт командой: 
```
python tg_bot.py
```


## Демонстрация

Вы можете протестировать работу данного бота.

* Напишите в [Telegram @ChGK_OWL_bot](https://telegram.me/ChGK_OWL_bot).
