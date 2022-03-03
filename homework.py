import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions as ex

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
URL = 'https://practicum.yandex.ru/'
API = 'api/user_api/homework_statuses/'

RETRY_TIME = 600
ENDPOINT = URL + API
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class ForTelegramHandler(logging.StreamHandler):
    """Хэндлер с возможностью отправки сообщения уровня error в чат."""

    def __init__(self, stream, bot=None):
        """Добавляет свойства класса."""
        super().__init__(stream)
        self.bot = bot
        self._last_error = "error"

    def emit(self, record):
        """Формирует и отправляет сообщения в телеграмм и консоль."""
        if self.bot and record.message != self._last_error:
            self._last_error = record.message
            log_error = self.format(record)
            self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=log_error)
        super().emit(record)

    def set_bot(self, t_bot):
        """Функция для определения бота."""
        self.bot = t_bot


def send_message(bot, message):
    """Отправляет сообщения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение отправлено')
    except ex.NegativeStatus as error:
        logger.error(f'Бот не смог отправить сообщение, ошибка {error}')


def get_api_answer(current_timestamp):
    """Делает запроса к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_status.status_code != HTTPStatus.OK:
            message = 'Сервер не отвечает'
            logger.error(message)
        else:
            return homework_status.json()
    except ex.NegativeStatus:
        message = 'Нет данных от сервера'
        logger.error(message)
        raise ex.NegativeStatus(message)


def check_response(response):
    """Проверяет ответ от API."""
    if type(response) != dict:
        message = 'Неправильный тип данных'
        logging.error(message)
        raise TypeError(message)
    if ['homeworks'][0] not in response:
        message = 'Нет поля homeworks в ответе'
        logger.error(message)
        raise IndexError(message)
    homeworks_list = response.get('homeworks')
    if len(homeworks_list) == 0:
        message = 'Нет домашних работ на проверке'
        logging.info(message)
    if type(homeworks_list) != list:
        message = 'Неправильный тип данных'
        logger.error(message)
        raise TypeError(message)
    return homeworks_list


def parse_status(homework):
    """Получает статус домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        message = 'Неизвестный статус'
        logger.error(message)
        raise ex.NegativeStatus(message)


def check_tokens():
    """Проверяет наличие токенов."""
    tokens_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    if not all(tokens_list):
        message = 'Отсутствуют токены'
        logging.critical(message)
        return False
    return True


def main(handler):
    """Основная логика работы бота."""
    check = check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    handler.set_bot(bot)
    current_timestamp = int(time.time())
    if check is False:
        message = 'Ошибка при проверке токенов'
        logging.critical(message)
        raise ex.NegativeToken
    try:
        message = 'Бот запустился'
        send_message(bot, message)
    except ex.NegativeStatus:
        message = 'Ошибка: Бот не запустился'
        logger.error(message)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if not response:
                logging.info('Ошибка при запросе')
                time.sleep(RETRY_TIME)
                continue
            if not response['homeworks']:
                logging.info('Нет новых проверенных работ')
                time.sleep(RETRY_TIME)
                continue
            homework = check_response(response)[0]
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except ex.NegativeStatus as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s  %(name)s',
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = ForTelegramHandler(sys.stdout)
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter(
        '%(asctime)s : %(levelname)s - %(message)s - %(name)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    main(handler)
