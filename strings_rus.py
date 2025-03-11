TOKENS_UNAVAILABLE = 'Нет токенов {unavailable_tokens}'
TOKENS_UNAVAILABLE_EXCEPTION = 'Один или несколько токенов недоступны'
ALL_TOKENS_AVAILABLE = 'Все токены на месте'
MESSAGE_SENT_SUCCESSULLY = 'Сообщение успешно отправлено: {message}'
MESSAGE_NOT_SENT = ('Ошибка при отправке сообщения: {error}.'
                      'Текст сообщения: {message}')
API_IS_UNAVAILABLE = ('API недоступен. Код ответа {status_code}, '
                      'ENDPOINT: {endpoint}, '
                      'ENDPOINT: {headers}, '
                      'params: {params}.')
API_ERROR = 'API вернул ошибку: {error}'
API_SUCCESS = 'Ответ от API получен успешно'
RESPONSE_TYPE_CHECK = ('Ответ API должен быть словарем, '
                       'а получен {response_type}')
NO_HOMEWORK_IN_RESPONSE = 'В ответе API отсутствует ключ "homeworks"'
RESPONSE_HOMEWORKS_TYPE_CHECK = ('Внутри homeworks должен быть список, '
                            'а получен {homework_type}')
HOMEWORK_WRONG_TYPE = ('Элементы "homeworks" должны быть словарями,'
                       'а получены {homework_type}')
RESPONSE_SUCCESS = 'Ответ API проверен успешно'
NO_HOMEWORK_NAME_IN_HOMEWORKS ='Ответ API не содержит ключ "homework_name"'
NO_HOMEWORK_NAME_KEY = 'В ответе API у "homework_name" отсутствует ключ'
UNKNOWN_HOMEWORK_STATUS = 'Неизвестный статус "{status}" в ответе API'
HOMEWORK_PROCESSED = 'Статус работы "{homework_name}" обработан: {verdict}.'
HOMEWORK_VERDICT = ('Изменился статус проверки работы "{homework_name}".'
                    '{verdict}')
MISSING_ENVIRONMENT_VARIABLE = 'Отсутствует переменная окружения'
PROGRAM_STOPPED = 'Программа принудительно остановлена'
ERROR_MESSAGE = 'Сбой в работе программы: {error}'
CONNECTION_ERROR = ('Ошибка соединения.'
                    'ENDPOINT: {endpoint}, '
                    'ENDPOINT: {headers}, '
                    'params: {params}.')
RESPONSE_NOT_JSON = 'Ошибка, ответ не в формате json, {error}'
TELEGRAM_MESSAGE_NOT_SUCCESSFUL = ('Не удалось отправить сообщение в Telegram, '
                                   'сообщение: {message}')