import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiException

from exceptions import APIIsUnavailableException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
stream_handler = logging.StreamHandler(sys.stdout)
formatter = (logging
             .Formatter('%(asctime)s, %(levelname)s, %(message)s'))
stream_handler.setFormatter(formatter)

logging.basicConfig(
    handlers=[stream_handler],
    level=logging.DEBUG,
)


def check_tokens():
    """Проверяет наличие токенов.
    Функция перебирает словарь обязательных переменных окружения (TOKEN_KEYS)
    и проверяет их наличие. Если какие-либо токены отсутствуют,
    записывает критическую ошибку в лог и вызывает исключение
    TokenNotFoundException.
    """
    TOKEN_KEYS = {'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
                  'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
                  'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}
    unavailable_tokens = []
    for token in TOKEN_KEYS:
        if TOKEN_KEYS[token] is None:
            unavailable_tokens.append(token)
    if unavailable_tokens:
        logging.critical(f'Нет токенов {", ".join(unavailable_tokens)}')
        return False
    else:
        logging.debug('Все токены на месте')
        return True


def send_message(bot, message):
    """Посылает сообщение в Telegram.
    Пытается послать сообщение в Telegram-чат, определяемый переменной
    окружения TELEGRAM_CHAT_ID.
    Если не может, вызывает ApiException.
    Args:
        bot (class 'telebot.TeleBot'): бот;
        message (str): сообщение
    """
    chat_id = TELEGRAM_CHAT_ID
    try:
        bot.send_message(chat_id, message)
        logging.debug(f'Сообщение успешно отправлено: {message}')
    except ApiException:
        logging.error(f'Ошибка при отправке сообщения: {ApiException}.')


def get_api_answer(timestamp):
    """Получает ответ API.
    Пытается получить ответ API и проверять его корректность. Если код ответа
    не равен 200, вызывает исключение APIIsUnavailableException.
    Если код правильный, возвращает отформатированный результат запроса.
    Args:
        timestamp (dict): временная метка;
    Returns:
        response.json(): ответ API.
    """
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=timestamp)
        if response.status_code != 200:
            logging.error(f'Неудачный запрос, код {response.status_code}')
            raise APIIsUnavailableException(
                f'API недоступен.'
                f'Код ответа {response.status_code}.')
        logging.debug('Ответ от API получен успешно')
        return response.json()
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к API Практикума: {error}')
        raise APIIsUnavailableException('Ошибка при запросе к API')


def check_response(response):
    """Проверяет ответ API на соответствие документации.
    Проверяет тип полученного ответа (должен быть словарь), вложенные в словарь
    response список homeworks и целочисленную переменнуую current_date и
    элементы списка homeworks, являющиеся словарями.
    Args:
        response (dict): ответ API;
    Returns:
        response.json(): ответ API.
    """
    try:
        if not isinstance(response, dict):
            raise TypeError('Ответ API должен быть словарем')
        if 'homeworks' not in response:
            raise KeyError('В ответе API отсутствует ключ "homeworks"')
        if not isinstance(response['homeworks'], list):
            raise TypeError('Внутри homeworks должен быть список')
        if 'current_date' not in response:
            raise KeyError('В ответе API отсутствует ключ "current_date"')
        if not isinstance(response['current_date'], int):
            raise TypeError('"current_date" должна быть целым числом')

        for homework in response['homeworks']:
            if not isinstance(homework, dict):
                raise TypeError('Элементы "homeworks" должны быть словарями')
        logging.debug('Ответ API проверен успешно')
        return response
    except (KeyError, TypeError) as error:
        logging.error(f"Ошибка в ответе API: {error}")
        raise


def parse_status(homework):
    """Извлекает из информации о последней домашней работе статус этой работы.
    Извлекает название и статус последней домашней работы, если они есть, и
    подставляет их в строку. Если нет, вызывает ошибку KeyError.
    Args:
        homework (dict): ответ API;
    Returns:
        str: строка с сообщением о статусе работы.
    """
    try:
        if 'homework_name' not in homework:
            raise KeyError("Ответ API не содержит ключ 'homework_name'")
        homework_name = homework['homework_name']
        if homework_name is None:
            raise KeyError("Ключ 'homework_name' отсутствует в ответе API")
        status = homework.get('status')
        if status not in HOMEWORK_VERDICTS:
            raise KeyError(f"Неизвестный статус '{status}' в ответе API")
        verdict = HOMEWORK_VERDICTS[homework['status']]
        logging.debug(f'Статус работы "{homework_name}" обработан: {verdict}')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logging.error(f"Ошибка в парсинге статуса: {error}")
        raise


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует переменная окружения')
        sys.exit('Программа принудительно остановлена')
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = {'from_date': int(time.time())}
    while True:
        try:
            response = get_api_answer(timestamp)
            message = check_response(response)
            if response['homeworks']:
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logging.error(f'Сбой в работе программы: {error}')
        timestamp['from_date'] = response['current_date']
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
