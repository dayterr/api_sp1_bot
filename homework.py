import logging
import os
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FORMAT = '%(asctime)s, %(levelname)s, %(message)s, %(name)s'

logging.basicConfig(
    level=logging.DEBUG,
    filename=os.path.join(BASE_DIR, 'yphwbot.log'),
    format=FORMAT,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('my_logger.log',
                              maxBytes=50000000,
                              backupCount=5)
logger.addHandler(handler)


try:
    PRAKTIKUM_TOKEN = os.environ['PRAKTIKUM_TOKEN']
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
    HEADERS = {'Authorization': f'OAuth {PRAKTIKUM_TOKEN}'}
    URL = 'https://praktikum.yandex.ru/api/user_api/homework_statuses/'
except (KeyError, NameError):
    logger.error('Токен не найден')


def parse_homework_status(homework):
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    stat_verdicts = {
        'rejected': 'К сожалению в работе нашлись ошибки.',
        'reviewing': 'Работа проверяется',
        'approved': ('Ревьюеру всё понравилось, '
                     'можно приступать к следующему уроку.')
    }
    if homework_name is None or status is None:
        logger.error('Неверный ответ сервера')
        return 'Произошла ошибка на сервере'
    verdict = stat_verdicts[status]
    return f'У Вас проверили работу "{homework_name}"!\n\n{verdict}'


def get_homework_statuses(current_timestamp):
    default_timestamp = int(time.time())
    params = {'from_date': current_timestamp or default_timestamp}
    try:
        homework_statuses = requests.get(url=URL,
                                         headers=HEADERS,
                                         params=params)
    except requests.exceptions.HTTPError:
        logger.error('Ошибка ответа сервера')
    return homework_statuses.json()


def send_message(message, bot_client):
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    logger.debug('Ботик запущен')

    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get('homeworks'):
                send_message(parse_homework_status(
                    new_homework.get('homeworks')[0]),
                    bot)
            if not new_homework.get('homeworks'):
                send_message('Работа проверяется', bot)
            logger.info('Сообщение отправлено')
            current_timestamp = new_homework.get('current_date',
                                                 current_timestamp)
            time.sleep(1500)

        except Exception as e:
            logger.error(f'Бот столкнулся с ошибкой: {e}')
            send_message(f'Бот столкнулся с ошибкой: {e}', bot)
            time.sleep(5)


if __name__ == '__main__':
    main()
