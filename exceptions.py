class NoDataExceptions(Exception):
    """Нет данных от сервера."""

    pass


class NegativeStatus(Exception):
    """Исключение при проверке статуса работы."""

    pass


class NegativeToken(Exception):
    """Класс исключений при проверке токенов."""

    pass


class SendException(Exception):
    """Ошибка при отправке сообщения."""

    pass


class ServerStatusException(Exception):
    """Статус ответа сервера не ОК."""

    pass


class BotRunException(Exception):
    """Ошибка при старте бота."""

    pass


class MainException(Exception):
    """Ошибка в работе main функции."""

    pass
