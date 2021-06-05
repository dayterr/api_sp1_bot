import datetime
import logging
import os
import sys
import time
from json.decoder import JSONDecodeError
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FORMAT = '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
LOG_NAME = os.path.join(BASE_DIR, 'yphwbot.log')

logging.basicConfig(
    handlers=[RotatingFileHandler(LOG_NAME, maxBytes=50000000, backupCount=5)],
    level=logging.INFO,
    format=FORMAT,
)


try:
    PRAKTIKUM_TOKEN = os.environ['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
except KeyError as e:
    logging.error(e, exc_info=True)
    sys.exit()

HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
TIME_TO_WAIT = 900


def parse_homework_status(homework):
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None or status is None:
        logging.error(f'Неверный ответ сервера: сервер вернул {homework}')
        return 'Произошла ошибка на сервере'
    stat_verdicts = {
        'rejected': 'К сожалению в работе нашлись ошибки.',
        'reviewing': f'Начата проверка работы {homework_name}',
        'approved': ('Ревьюеру всё понравилось, '
                     'можно приступать к следующему уроку.')
    }
    verdict = stat_verdicts.get(status)
    if verdict is None:
        msg = f'Неизвестный статус: {verdict}'
        logging.error(msg)
        return msg
    if status == 'reviewing':
        return verdict
    return f'У вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homework_statuses(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(url=URL,
                                         headers=HEADERS,
                                         params=params)
    except requests.exceptions.HTTPError as e:
        logging.error(e, exc_info=True)
    try:
        hw_json = homework_statuses.json()
    except JSONDecodeError as e:
        logging.error(e, exc_info=True)
    return hw_json


def send_message(message, bot_client):
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    start_msg = 'Ботик запущен'
    logging.debug(start_msg)
    send_message(start_msg, bot)
    status_cache = ''
    start_time = int(time.time())

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('homeworks'):
                hw_status = parse_homework_status(
                    new_homework.get('homeworks')[0])
                if 'проверка' in hw_status:
                    status_cache = 'reviewing'
                if 'ошибки' in hw_status or 'можно' in hw_status:
                    status_cache = 'reviewed'
                send_message(hw_status, bot)
                logging.info(f'Сообщение "{hw_status}" отправлено')
                status_cache = ''
            time_passed = int(time.time()) - start_time
            mns = datetime.datetime.now().minute
            if not new_homework.get('homeworks') and mns <= 15:
                hrs = int(time.strftime("%H", time.gmtime(time_passed)))
                msg = ''
                if not status_cache:
                    msg = 'Работа в ожидании, '
                if status_cache == 'reviewing':
                    msg = 'Работа проверяется, '
                msg += f'прошло {hrs} h'
                send_message(msg, bot)
                logging.info(f'Сообщение "{msg}" отправлено')
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            time.sleep(TIME_TO_WAIT)

        except Exception as exc:
            msg = f'Бот столкнулся с ошибкой: {exc}'
            logging.error(msg)
            send_message(msg, bot)
            time.sleep(5)


if __name__ == '__main__':
    main()
