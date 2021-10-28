import requests as r
import time
from icecream import ic
import logging
import asyncio
import aiohttp
import json

telegram_token_file = "telegram_token.txt"
with open('telegram_token.txt') as tf:
    telegram_token = tf.readline()
binance_url = "https://api2.binance.com"
telegram_url = f"https://api.telegram.org/bot{telegram_token}"
currencies = ["BTCUSDT", "SHIBUSDT", "DOGEUSDT", "ETHUSDT", "FTMUSDT"]
url_currencies = [binance_url + f'/api/v3/avgPrice?symbol={currency}'
                  for currency in currencies]
keyboard = json.dumps(
    {"keyboard": [[{"text": "/update"}]], "one_time_keyboard": True})


# Functions to interact with Telegram bot.
def get_all_updates(offset=0):
    return r.get(telegram_url + f"/getUpdates?offset={offset}").json()
def get_update_id(updates): return updates["result"][-1]["update_id"]


def get_chat_id(update):
    try:
        chat_id = update["message"]["from"]["id"]
    except Exception:
        return None
    else:
        return chat_id
def get_text(update):
    try:
        text = update["message"]["text"]
    except Exception:
        return None
    else:
        return text


def send_message(chat_id, text, interface=None, parse_mode='HTML'):
    url = telegram_url + \
        f"/sendMessage?chat_id={chat_id}&text={text}&parse_mode={parse_mode}"
    if interface:
        url += f"&reply_markup={interface}"
    r.post(url).content


# Functions to extact data from Binance API.
def ping_bin(): return r.get(binance_url + "/api/v3/ping")
async def a_get_price(url, session):
    """Returns price for a coin in USD.

    Args:
        url:
            Full url of the method avgPrice.
        session:
            Current session of the aiohttp.ClientSession() call.

    Returns:
        String in format: <Coin name> <Coin price in USD>$
    """
    try:
        async with session.get(url) as response:
            price = float((await response.json())["price"])
            price = str(round(price, 2)) if price > 0.0001 else str(
                f'{price:f}')
            price = '<strong>' + url.split('=')[-1].split("USDT")[0] + '</strong>' + \
                " " + str(price) + "$\n"
        return price
    except Exception as e:
        print(f"Unable to get url {url} due to {e.__class__}.")


async def a_get_prices(urls):
    """Returns list of prices for coins in USD.

    Args:
        urls:
            List of urls of the method avgPrice for each coin.

    Returns:
        List of prices as strings in format: <Coin name> <Coin price in USD>$
    """
    async with aiohttp.ClientSession() as session:
        prices = await asyncio.gather(*[a_get_price(url, session) for url in urls])
    return prices

logging.basicConfig(encoding='utf-8',
                    level=logging.DEBUG, filename='binance_bot.log', format='%(asctime)s %(levelname)s:%(message)s', datefmt='%F %H:%M:%S')


def main():
    """Checks bot for updates and posts market data upon receiving /update    command."""
    offset = 0
    while True:
        updates = get_all_updates(offset)
        try:
            offset = get_update_id(updates) + 1
        except IndexError:
            continue
        for update in updates["result"]:
            {k: str(v).encode("utf-8") for k, v in update.items()}
            chat_id = get_chat_id(update)
            if chat_id:
                logging.info('A message will be sent!')
                msg_text = ""
                if get_text(update) == "/update":
                    for price in asyncio.get_event_loop().run_until_complete(a_get_prices(url_currencies)):
                        msg_text += price
                    send_message(chat_id, msg_text)
                elif get_text(update) == "/start":
                    msg_text = "To get the latest prices for BTC, SHIB, DOGE, ETH and FTM send <b>/update</b>."
                    send_message(chat_id, msg_text, keyboard)
                else:
                    msg_text = "You probably meant <b><i>/update</i></b>."
                    send_message(chat_id, msg_text, keyboard)
        time.sleep(1)


if __name__ == "__main__":
    main()
