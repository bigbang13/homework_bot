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


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class ForTelegramHandler(logging.StreamHandler):
    """Хэндлер с возможностью отправки сообщения уровня error в чат."""

    def __init__(self, stream, bot=None):
        """Добавляет свойства класса."""
        super().__init__(stream)
        self.bot = telegram.Bot(token=TELEGRAM_TOKEN)
        self._last_error = "error"

    def emit(self, record):
        """Формирует и отправляет сообщения в телеграмм и консоль."""
        if self.bot and record.message != self._last_error:
            self._last_error = record.message
            log_error = self.format(record)
            self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=log_error)
        super().emit(record)

    def set_bot(self):
        """Функция для определения бота."""
        bot = self.bot
        return bot


def send_message(bot, message):
    """Отправляет сообщения."""
    try:
        logging.info('Отправляем сообщение')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except ex.SendException as error:
        logger.error(f'Бот не смог отправить сообщение, ошибка {error}')
    else:
        logging.info('Сообщение отправлено')


def get_api_answer(current_timestamp):
    """Делает запроса к API."""
    timestamp = current_timestamp or int(time.time())
    request_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logging.info('Делаем запрос к API')
        homework_status = requests.get(**request_params)
        if homework_status.status_code != HTTPStatus.OK:
            message = 'Сервер не отвечает'
            logger.error(message)
            raise ex.ServerStatusException(request_params)
        return homework_status.json()
    except ex.NoDataExceptions:
        message = 'Нет данных от сервера'
        logger.error(message)
        raise ex.NoDataExceptions(message)


def check_response(response):
    """Проверяет ответ от API."""
    if not isinstance(response, dict):
        message = 'Неправильный тип данных'
        logging.error(message)
        raise TypeError(message)
    if ('homeworks' and 'current_date') not in response:
        message = 'Отсутствует обязательное поле в ответе'
        raise KeyError(message)
    homeworks_list = response.get('homeworks')
    if not homeworks_list:
        message = 'Нет домашних работ на проверке'
    if not isinstance(homeworks_list, list):
        message = 'Неправильный тип данных'
        raise ValueError(message)
    return homeworks_list


def parse_status(homework):
    """Получает статус домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_name and homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    else:
        message = 'Неизвестный статус'
        raise ex.NegativeStatus(message)


def check_tokens():
    """Проверяет наличие токенов."""
    tokens_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    if not all(tokens_list):
        return False
    return True


def main(handler):
    """Основная логика работы бота."""
    prev_message = ''
    bot = handler.set_bot()
    current_timestamp = int(time.time())
    if not check_tokens():
        message = 'Ошибка при проверке токенов'
        logging.critical(message)
        sys.exit(message)
    try:
        message = 'Бот запустился'
        send_message(bot, message)
    except ex.BotRunException:
        message = 'Ошибка: Бот не запустился'
        logger.error(message)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            if not response:
                logging.info('Ошибка при запросе')
                continue
            if not response['homeworks']:
                logging.info('Нет новых проверенных работ')
                continue
            homework = check_response(response)[0]
            message = parse_status(homework)
            if prev_message != message:
                send_message(bot, message)
                prev_message = message
            current_timestamp = int(time.time())

        except ex.MainException as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='a',
        format=('%(asctime)s - %(levelname)s - %(funcName)s - '
                '%(lineno)d - %(message)s - %(name)s'),
    )
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = ForTelegramHandler(sys.stdout)
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter((
        '%(asctime)s : %(levelname)s - %(funcName)s - '
        '%(lineno)d - %(message)s - %(name)s')
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    main(handler)
