import math
from collections.abc import Callable
from datetime import datetime

from ..infra.settings import SettingsLoader
from .currencies import CurrencyRegistry
from .decorators import log_action
from .exceptions import ApiRequestError
from .models import Portfolio, RateInfo, User, Wallet


def register(username: str, password: str) -> str:
    """Регистрирует пользователя и создает ему пустой портфель."""
    all_users = User.load_users()
    _assert_username_uniq(all_users, username)
    new_user = User.create_user(
        _get_next_id(all_users, "user_id"), username, password
    )
    new_user.update_user_db()

    new_portfolio = Portfolio.create_for_user(new_user)
    new_portfolio.update_portfolios_db()

    return (
        f"Пользователь '{username}' зарегистрирован (id={new_user.user_id}). "
        f"Войдите: login --username {username} --password ****"
    )


def login(username: str, password: str) -> User:
    """Аутентифицирует пользователя по имени и паролю."""
    all_users = User.load_users()
    user = next((u for u in all_users if u.username == username), None)
    if user is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    password_check = user.verify_password(password)
    if not password_check:
        raise ValueError("Неверный пароль")

    return user


def show_portfolio(user: User | None, base: str) -> str:
    """Возвращает портфель пользователя в базовой валюте."""
    _validate_login(user)
    CurrencyRegistry().get_currency(base)
    rate_info = RateInfo.load_rate_info()
    user_port = _load_user_portfolio(user)

    if not user_port.wallets:
        return f"У пользователя '{user.username}' нет кошельков"
    else:
        result = f"Портфель пользователя '{user.username}' (база: {base}):\n"
        for wallet in user_port.wallets.values():
            value = wallet.get_total_value(rate_info, base)
            result += (
                f"- {wallet.currency_code}: {wallet.balance:.4f}  "
                f"→ {value:,.2f} {base}\n"
            )
        result += "-" * 33 + "\n"
        result += f"ИТОГО: {user_port.get_total_value(base):,.2f} {base}"
        return result


@log_action("buy")
def buy(user: User | None, currency: str, amount: float) -> str:
    """Покупает валюту за счет кошелька опорной валюты."""
    user_port, rate = _prepare_trade(user, currency, amount)
    cost = amount * rate

    pivot_currency = SettingsLoader().get_pivot_currency()
    pivot_change = ""
    if currency != pivot_currency:
        pivot_wallet = user_port.get_wallet(pivot_currency)
        pivot_change = _apply_change(pivot_wallet, pivot_wallet.withdraw, cost)

    wallet = _get_or_create_wallet(user_port, currency)
    wallet_change = _apply_change(wallet, wallet.deposit, amount)
    user_port.update_portfolios_db()

    return _format_trade(
        "Покупка",
        currency,
        amount,
        rate,
        wallet_change + pivot_change,
        f"Оценочная стоимость покупки: {cost:,.2f} {pivot_currency}",
    )


@log_action("sell")
def sell(user: User | None, currency: str, amount: float) -> str:
    """Продает валюту с зачислением выручки в опорную валюту."""
    user_port, rate = _prepare_trade(user, currency, amount)
    revenue = amount * rate

    wallet = user_port.get_wallet(currency)
    wallet_change = _apply_change(wallet, wallet.withdraw, amount)

    pivot_change = ""
    pivot_currency = SettingsLoader().get_pivot_currency()
    if currency != pivot_currency:
        pivot_wallet = _get_or_create_wallet(user_port, pivot_currency)
        pivot_change = _apply_change(
            pivot_wallet, pivot_wallet.deposit, revenue
        )
    user_port.update_portfolios_db()

    return _format_trade(
        "Продажа",
        currency,
        amount,
        rate,
        wallet_change + pivot_change,
        f"Оценочная выручка: {revenue:,.2f} {pivot_currency}",
    )


def get_rate(from_currency: str, to_currency: str) -> str:
    """Возвращает прямой и обратный курс между валютами."""
    registry = CurrencyRegistry()
    registry.get_currency(from_currency)
    registry.get_currency(to_currency)
    rate_info = RateInfo.load_rate_info()
    if _is_cache_stale(rate_info):
        rate_info = _refresh_rates()
    try:
        rate = rate_info.convert(1.0, from_currency, to_currency)
        updated_at = rate_info.get_updated_at(from_currency, to_currency)
    except ValueError as e:
        raise ValueError(
            f"Курс {from_currency}→{to_currency} недоступен. "
            "Повторите попытку позже."
        ) from e

    return (
        f"Курс {from_currency}→{to_currency}: {_format_rate(rate)} "
        f"(обновлено: {updated_at:%Y-%m-%d %H:%M:%S})\n"
        f"Обратный курс {to_currency}→{from_currency}: "
        f"{_format_rate(1 / rate)}"
    )


def _assert_username_uniq(users, new_name):
    if any(u.username == new_name for u in users):
        raise ValueError(f"Имя пользователя '{new_name}' уже занято")


def _get_next_id(items, id_field_name):
    """Возвращает следующий свободный идентификатор."""
    all_ids = [getattr(item, id_field_name) for item in items]
    return max(all_ids) + 1 if all_ids else 1


def _is_cache_stale(rate_info: RateInfo) -> bool:
    """Проверяет, устарел ли кеш курсов."""
    age = datetime.now() - rate_info.last_refresh
    return age.total_seconds() > SettingsLoader().get_rates_ttl_seconds()


def _refresh_rates() -> RateInfo:
    """Обновляет кеш курсов."""
    raise ApiRequestError("сервис обновления курсов недоступен")


def _prepare_trade(
    user: User | None, currency: str, amount: float
) -> tuple[Portfolio, float]:
    """Проверяет данные сделки и возвращает портфель и курс."""
    _validate_login(user)
    CurrencyRegistry().get_currency(currency)
    pivot_currency = SettingsLoader().get_pivot_currency()
    rate = RateInfo.load_rate_info().convert(1.0, currency, pivot_currency)
    _validate_amount(amount)
    return _load_user_portfolio(user), rate


def _validate_login(user: User | None) -> None:
    if user is None:
        raise ValueError("Сначала выполните login")


def _load_user_portfolio(user: User) -> Portfolio:
    all_ports = Portfolio.load_portfolios()
    user_port = next((p for p in all_ports if p.user_id == user.user_id), None)
    if user_port is None:
        raise ValueError(f"Портфель пользователя '{user.username}' не найден")
    return user_port


def _validate_amount(amount: float) -> None:
    if (
        isinstance(amount, bool)
        or not isinstance(amount, (int, float))
        or not math.isfinite(amount)
        or amount <= 0
    ):
        raise ValueError("'amount' должен быть положительным числом")


def _get_or_create_wallet(portfolio: Portfolio, currency: str) -> Wallet:
    """Возвращает кошелек валюты, создавая его при отсутствии."""
    wallet = portfolio.wallets.get(currency)
    if wallet is None:
        wallet = portfolio.add_currency(currency)
    return wallet


def _apply_change(
    wallet: Wallet, operation: Callable[[float], None], amount: float
) -> str:
    """Применяет операцию к кошельку и описывает изменение баланса."""
    balance_before = wallet.balance
    operation(amount)
    return (
        f"- {wallet.currency_code}: было {balance_before:.4f} "
        f"→ стало {wallet.balance:.4f}\n"
    )


def _format_trade(
    action: str,
    currency: str,
    amount: float,
    rate: float,
    changes: str,
    summary: str,
) -> str:
    """Форматирует сообщение о выполненной сделке."""
    pivot_currency = SettingsLoader().get_pivot_currency()
    return (
        f"{action} выполнена: {amount:.4f} {currency} по курсу "
        f"{rate:,.2f} {pivot_currency}/{currency}\n"
        "Изменения в портфеле:\n"
        f"{changes}"
        f"{summary}"
    )


def _format_rate(rate: float) -> str:
    """Форматирует курс для вывода."""
    return f"{rate:.8f}" if rate < 1 else f"{rate:,.2f}"
