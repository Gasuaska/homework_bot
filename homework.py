from http import HTTPStatus
import logging
import os
import sys
import time

import requests
import requests.exceptions
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.apihelper import ApiException

from exceptions import ApiError, APIIsUnavailableError, TelegramConnectionError, TokenNotFoundError, MessageError
from strings_rus import *

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

TOKEN_NAMES = {'PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID'}


def check_tokens():
    """Проверяет наличие токенов.
    Функция перебирает словарь обязательных переменных окружения (TOKEN_KEYS)
    и проверяет их наличие. Если какие-либо токены отсутствуют,
    записывает критическую ошибку в лог и вызывает исключение
    TokenNotFoundException.
    """
    unavailable_tokens = [token for token in TOKEN_NAMES
                          if not globals().get(token)]
    if unavailable_tokens:
        logging.critical(TOKENS_UNAVAILABLE.
                         format(unavailable_tokens=unavailable_tokens))
        raise TokenNotFoundError(TOKENS_UNAVAILABLE.
                                 format(unavailable_tokens=unavailable_tokens))
    logging.debug(ALL_TOKENS_AVAILABLE)


def send_message(bot, message):
    """Посылает сообщение в Telegram.
    Пытается послать сообщение в Telegram-чат, определяемый переменной
    окружения TELEGRAM_CHAT_ID.
    Если не может, вызывает ApiError.
    Args:
        bot (class 'telebot.TeleBot'): бот;
        message (str): сообщение
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(MESSAGE_SENT_SUCCESSULLY.format(message=message))
        return True
    except ApiException as error:
        logging.exception(MESSAGE_NOT_SENT.format(error=error,
                                                  message=message))
        return False

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
    except requests.exceptions.RequestException as error:
        raise TelegramConnectionError(CONNECTION_ERROR.format(
            error=error,
            url=ENDPOINT,
            headers=HEADERS,
            params=timestamp,
        ))
    if response.status_code != HTTPStatus.OK:
        raise APIIsUnavailableError(API_IS_UNAVAILABLE.format(
            status_code=response.status_code,
            endpoint=ENDPOINT,
            headers=HEADERS,
            params=timestamp,
            ))
    try:
        response_json = response.json()
        if any(key in response_json for key in ('code', 'error')):
            raise APIIsUnavailableError(API_ERROR.format(error=response_json))
        logging.debug(API_SUCCESS)
        return response_json
    except Exception as error:
        raise ResponseFormatError(RESPONSE_NOT_JSON.format(error))


def check_response(response):
    """Проверяет ответ API на соответствие документации.
    Проверяет тип полученного ответа (должен быть словарь), вложенные в словарь
    response список homeworks и целочисленную переменную current_date и
    элементы списка homeworks, являющиеся словарями.
    Args:
        response (dict): ответ API;
    Returns:
        response.json(): ответ API.
    """
    if not isinstance(response, dict):
        raise TypeError(RESPONSE_TYPE_CHECK.format(
            response_type=type(response)))
    if 'homeworks' not in response:
        raise KeyError(NO_HOMEWORK_IN_RESPONSE)
    if not isinstance(response['homeworks'], list):
        raise TypeError(RESPONSE_HOMEWORKS_TYPE_CHECK.format(
            homework_type=type(response['homeworks'])))
    for homework in response['homeworks']:
        if not isinstance(homework, dict):
            raise TypeError(HOMEWORK_WRONG_TYPE.format(
                homework_type=type(homework)))
    logging.debug(RESPONSE_SUCCESS)


def parse_status(homework):
    """Извлекает из информации о последней домашней работе статус этой работы.
    Извлекает название и статус последней домашней работы, если они есть, и
    подставляет их в строку. Если нет, вызывает ошибку KeyError.
    Args:
        homework (dict): ответ API;
    Returns:
        str: строка с сообщением о статусе работы.
    """
    if 'homework_name' not in homework:
        raise KeyError(NO_HOMEWORK_NAME_IN_HOMEWORKS)
    homework_name = homework['homework_name']
    if homework_name is None:
        raise ValueError(NO_HOMEWORK_NAME_KEY)
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError(UNKNOWN_HOMEWORK_STATUS.format(status=status))
    verdict = HOMEWORK_VERDICTS[status]
    logging.debug(HOMEWORK_PROCESSED.format(homework_name=homework_name,
                                          verdict=verdict))
    return HOMEWORK_VERDICT.format(homework_name=homework_name,
                                   verdict=verdict)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = {'from_date': int(time.time())}
    while True:
        try:
            response = get_api_answer(timestamp)
            message = check_response(response)
            if response['homeworks']:
                message = parse_status(response['homeworks'][0])
                if not send_message(bot, message):  
                    logging.error(TELEGRAM_MESSAGE_NOT_SUCCESSFUL.
                                  format(message=message))
                timestamp['from_date'] = response.get('current_date',
                                                      timestamp['from_date'])
        except Exception as error:
            logging.error(ERROR_MESSAGE.format(error=error))
            message = ERROR_MESSAGE.format(error=error)
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)])
    main()