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

import exceptions

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

TOKENS_UNAVAILABLE = 'Нет токенов {unavailable_tokens}.'
TOKENS_UNAVAILABLE_EXCEPTION = 'Один или несколько токенов недоступны.'
ALL_TOKENS_AVAILABLE = 'Все токены на месте.'
MESSAGE_SENT_SUCCESSULLY = 'Сообщение успешно отправлено: {message}.'
MESSAGE_NOT_SENT = ('Ошибка при отправке сообщения: {error}.'
                    'Текст сообщения: {message}.')
API_IS_UNAVAILABLE = ('API недоступен. Код ответа {status_code}, '
                      'ENDPOINT: {endpoint}, '
                      'ENDPOINT: {headers}, '
                      'params: {params}.')
API_ERROR = ('API вернул ошибку: {key}: {value}. '
             'ENDPOINT: {endpoint}, '
             'ENDPOINT: {headers}, '
             'params: {params}.')
API_SUCCESS = 'Ответ от API получен успешно.'
RESPONSE_TYPE_CHECK = ('Ответ API должен быть словарем, '
                       'а получен {response_type}.')
NO_HOMEWORK_IN_RESPONSE = 'В ответе API отсутствует ключ "homeworks".'
RESPONSE_HOMEWORKS_TYPE_CHECK = ('Внутри homeworks должен быть список, '
                                 'а получен {homework_type}.')
HOMEWORK_WRONG_TYPE = ('Элементы "homeworks" должны быть словарями,'
                       'а получены {homework_type}.')
RESPONSE_SUCCESS = 'Ответ API проверен успешно.'
NO_HOMEWORK_NAME_IN_HOMEWORKS = 'Ответ API не содержит ключ "homework_name"'
NO_HOMEWORK_NAME_KEY = 'В ответе API у "homework_name" отсутствует ключ.'
UNKNOWN_HOMEWORK_STATUS = 'Неизвестный статус "{status}" в ответе API.'
HOMEWORK_PROCESSED = 'Статус работы "{homework_name}" обработан: {verdict}'
HOMEWORK_VERDICT = ('Изменился статус проверки работы "{homework_name}": '
                    '{verdict}')
MISSING_ENVIRONMENT_VARIABLE = 'Отсутствует переменная окружения.'
PROGRAM_STOPPED = 'Программа принудительно остановлена.'
ERROR_MESSAGE = 'Сбой в работе программы: {error}.'
CONNECTION_ERROR = ('Ошибка соединения. '
                    'ENDPOINT: {endpoint}, '
                    'ENDPOINT: {headers}, '
                    'params: {params}.')
RESPONSE_NOT_JSON = 'Ошибка, ответ не в формате json, {error}.'
TELEGRAM_MESSAGE_NOT_SUCCESSFUL = ('Не удалось отправить сообщение в Telegram,'
                                   ' сообщение: {message}.')
NO_NEW_HOMEWORKS = 'Обновлений по домашним работам нет. Жду {period} минут.'
MESSAGE_SUCCESSFULY_SENT = 'Сообщение успешно отправлено.'

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
        logging.critical(
            TOKENS_UNAVAILABLE.format(unavailable_tokens=unavailable_tokens))
        raise ValueError(
            TOKENS_UNAVAILABLE.format(unavailable_tokens=unavailable_tokens))
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
        logging.exception(
            MESSAGE_NOT_SENT.format(error=error, message=message))
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
    timestamp = {'from_date': timestamp}
    request_params = dict(url=ENDPOINT, headers=HEADERS, params=timestamp)
    try:
        response = requests.get(**request_params)
    except requests.exceptions.RequestException as error:
        raise ConnectionError(
            CONNECTION_ERROR.format(
                error=error,
                **request_params))
    if response.status_code != HTTPStatus.OK:
        raise exceptions.APIIsUnavailableError(API_IS_UNAVAILABLE.format(
            status_code=response.status_code,
            **request_params))
    response_json = response.json()
    for key in ('code', 'error'):
        if key in response_json:
            raise exceptions.ResponseFormatError(
                API_ERROR.format(
                    key=key,
                    value=response_json[key],
                    **request_params))
    logging.debug(API_SUCCESS)
    return response_json


def check_response(response):
    """Проверяет ответ API на соответствие документации.
    Проверяет тип полученного ответа (должен быть словарь), вложенные в словарь
    response список homeworks и целочисленную переменную current_date и
    элементы списка homeworks, являющиеся словарями.
    Args:
        response (dict): ответ API;
    """
    if not isinstance(response, dict):
        raise TypeError(RESPONSE_TYPE_CHECK.format(
            response_type=type(response)))
    if 'homeworks' not in response:
        raise KeyError(NO_HOMEWORK_IN_RESPONSE)
    homework = response['homeworks']
    if not isinstance(homework, list):
        raise TypeError(RESPONSE_HOMEWORKS_TYPE_CHECK.format(
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
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(UNKNOWN_HOMEWORK_STATUS.format(status=status))
    verdict = HOMEWORK_VERDICTS[status]
    logging.debug(HOMEWORK_PROCESSED.format(
        homework_name=homework_name,
        verdict=verdict))
    return HOMEWORK_VERDICT.format(
        homework_name=homework_name,
        verdict=verdict)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = None
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response['homeworks']
            if not homework:
                logging.info(NO_NEW_HOMEWORKS)
                continue
            message = parse_status(homework[0])
            if send_message(bot, message):
                logging.debug(MESSAGE_SUCCESSFULY_SENT.
                              format(period=RETRY_PERIOD / 60))
                timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = ERROR_MESSAGE.format(error=error)
            logging.error(message)
            if message != last_message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[logging.FileHandler(f'{__file__}.log', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)])
    main()
