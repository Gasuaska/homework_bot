class APIIsUnavailableError(Exception):
    pass


class TelegramConnectionError(Exception):
    pass


class TokenNotFoundError(Exception):
    pass

class ApiError(Exception):
    pass


class MessageError(Exception):
    pass