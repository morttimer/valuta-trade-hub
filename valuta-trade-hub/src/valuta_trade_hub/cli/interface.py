import argparse
import shlex
from typing import NoReturn

from ..core import usecases
from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from ..core.models import User
from ..infra.settings import SettingsLoader


class CliError(Exception):
    pass


class ReplArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        """Выбрасывает CliError при ошибке разбора аргументов."""
        raise CliError(message)

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        """Выбрасывает CliError вместо завершения программы."""
        raise CliError(message or "")


def run() -> None:
    """Запускает интерактивный цикл команд CLI."""
    parser = _build_parser()
    current_user: User | None = None

    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if not line.strip():
            continue

        try:
            args = parser.parse_args(shlex.split(line))
        except (CliError, ValueError) as e:
            if str(e):
                print(e)
            continue

        try:
            match args.command:
                case "register":
                    print(usecases.register(args.username, args.password))
                case "login":
                    current_user = usecases.login(args.username, args.password)
                    print(f"Вы вошли как '{current_user.username}'")
                case "show-portfolio":
                    print(usecases.show_portfolio(current_user, args.base))
                case "buy":
                    print(
                        usecases.buy(current_user, args.currency, args.amount)
                    )
                case "sell":
                    print(
                        usecases.sell(current_user, args.currency, args.amount)
                    )
                case "get-rate":
                    print(
                        usecases.get_rate(args.from_currency, args.to_currency)
                    )
                case "exit":
                    break
        except InsufficientFundsError as e:
            print(e)
        except CurrencyNotFoundError as e:
            print(f"{e}. См. 'get-rate -h'")
        except ApiRequestError as e:
            print(f"{e}. Повторите попытку позже")
        except (ValueError, TypeError) as e:
            print(e)


def _build_parser() -> ReplArgumentParser:
    """Создает парсер команд CLI."""
    parser = ReplArgumentParser(prog="")
    commands = parser.add_subparsers(dest="command", required=True)

    register = commands.add_parser(
        "register", help="зарегистрировать пользователя"
    )
    register.add_argument("--username", required=True)
    register.add_argument("--password", required=True)

    login = commands.add_parser("login", help="войти в систему")
    login.add_argument("--username", required=True)
    login.add_argument("--password", required=True)

    show_portfolio = commands.add_parser(
        "show-portfolio", help="показать портфель"
    )
    show_portfolio.add_argument(
        "--base", default=SettingsLoader().get_default_base_currency()
    )

    buy = commands.add_parser("buy", help="купить валюту")
    buy.add_argument("--currency", required=True)
    buy.add_argument("--amount", required=True, type=float)

    sell = commands.add_parser("sell", help="продать валюту")
    sell.add_argument("--currency", required=True)
    sell.add_argument("--amount", required=True, type=float)

    get_rate = commands.add_parser("get-rate", help="показать курс валюты")
    get_rate.add_argument("--from", dest="from_currency", required=True)
    get_rate.add_argument("--to", dest="to_currency", required=True)

    commands.add_parser("exit", help="выйти из программы")

    return parser
