class APIIsUnavailableError(Exception):
    pass


class TelegramConnectionError(Exception):
    pass


class TokenNotFoundError(Exception):
    pass

class ResponseFormatError(Exception):
    pass