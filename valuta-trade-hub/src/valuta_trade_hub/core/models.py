import hashlib
import math
from datetime import datetime
from os import urandom
from typing import Self

from ..core.exceptions import InsufficientFundsError
from ..infra.settings import SettingsLoader
from .utils import load_json, save_json


class RateInfo:
    def __init__(self, rates, source, last_refresh):
        self._rates = rates
        self._source = source
        self._last_refresh = last_refresh

    def convert(self, amount: float, curr_from: str, curr_to: str) -> float:
        """Конвертирует сумму между валютами через опорную валюту."""
        return (
            amount
            * self._rate_to_pivot(curr_from)
            / self._rate_to_pivot(curr_to)
        )

    def _rate_to_pivot(self, currency_code: str) -> float:
        """Возвращает курс валюты к опорной валюте."""
        pivot_currency = SettingsLoader().get_pivot_currency()
        if currency_code == pivot_currency:
            return 1.0
        return self.find_rate(currency_code, pivot_currency)

    def find_rate(self, curr_from, curr_to):
        """Возвращает курс для пары валют."""
        return self._find_rate_entry(curr_from, curr_to).rate

    def get_updated_at(self, curr_from: str, curr_to: str) -> datetime:
        """Возвращает время обновления курса для пары валют."""
        pivot_currency = SettingsLoader().get_pivot_currency()
        timestamps = [
            datetime.fromisoformat(
                self._find_rate_entry(code, pivot_currency).updated_at
            )
            for code in (curr_from, curr_to)
            if code != pivot_currency
        ]
        return min(
            timestamps, default=datetime.fromisoformat(self._last_refresh)
        )

    def _find_rate_entry(self, curr_from: str, curr_to: str) -> "Rate":
        """Возвращает запись курса для пары валют."""
        for rate in self._rates:
            if rate.currency_from == curr_from and rate.currency_to == curr_to:
                return rate
        raise ValueError(f"Не удалось получить курс для {curr_from}→{curr_to}")

    @property
    def rates(self):
        return self._rates

    @property
    def last_refresh(self) -> datetime:
        return datetime.fromisoformat(self._last_refresh)

    @staticmethod
    def _parse_currency(key) -> tuple[str, str]:
        underscore_pos = key.find("_")
        return (key[:underscore_pos], key[underscore_pos + 1 :])

    @staticmethod
    def _is_rate_entry(key) -> bool:
        underscore_pos = key.find("_")
        return len(key) == 7 and underscore_pos != -1

    @classmethod
    def load_rate_info(cls) -> Self:
        """Загружает курсы валют из хранилища."""
        rate_info_json = load_json(SettingsLoader().get_db_rates_path())

        rates = []
        for key in rate_info_json:
            if RateInfo._is_rate_entry(key):
                currency_from, currency_to = RateInfo._parse_currency(key)
                rates.append(
                    Rate(
                        currency_from,
                        currency_to,
                        rate_info_json[key]["rate"],
                        rate_info_json[key]["updated_at"],
                    )
                )
        return cls(
            rates, rate_info_json["source"], rate_info_json["last_refresh"]
        )


class Rate:
    def __init__(self, currency_from, currency_to, rate, updated_at) -> None:
        self._currency_from = currency_from
        self._currency_to = currency_to
        self._rate = rate
        self._updated_at = updated_at

    def __str__(self):
        return (
            f"Currency_from: {self._currency_from}, "
            f"currency_to: {self._currency_to}, "
            f"rate: {self._rate}, updated_at: {self._updated_at}"
        )

    @property
    def currency_from(self):
        return self._currency_from

    @property
    def currency_to(self):
        return self._currency_to

    @property
    def rate(self):
        return self._rate

    @property
    def updated_at(self) -> str:
        return self._updated_at


class User:
    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @classmethod
    def create_user(cls, user_id: int, username: str, password: str) -> Self:
        """Создает пользователя с захешированным паролем."""
        User._assert_password_len(password)
        hashed_password, salt = User._generate_pass_and_salt(password)

        return cls(user_id, username, hashed_password, salt, datetime.now())

    @staticmethod
    def _generate_pass_and_salt(password: str) -> tuple[str, str]:
        salt = urandom(10).hex()
        hashed_password = User._hash_password(password, salt)
        return (hashed_password, salt)

    @classmethod
    def load_users(cls) -> list[Self]:
        """Загружает всех пользователей из хранилища."""
        json_list = load_json(SettingsLoader().get_db_users_path())
        user_list = []
        for user_json in json_list:
            user_list.append(
                cls(
                    user_json["user_id"],
                    user_json["username"],
                    user_json["hashed_password"],
                    user_json["salt"],
                    datetime.fromisoformat(user_json["registration_date"]),
                )
            )

        return user_list

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not value:
            raise ValueError("Имя пользователя не может быть пустым")
        else:
            self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> str:
        """Возвращает информацию о пользователе."""
        return self.__str__()

    def __str__(self) -> str:
        return (
            f"Пользователь '{self._username}' (id={self._user_id}), "
            f"дата регистрации: {self._registration_date:%Y-%m-%d %H:%M:%S}"
        )

    def change_password(self, new_password: str) -> None:
        """Меняет пароль пользователя и сохраняет его."""
        User._assert_password_len(new_password)
        new_salt = urandom(10).hex()
        hashed_password = User._hash_password(new_password, new_salt)

        self._salt = new_salt
        self._hashed_password = hashed_password
        self.update_user_db()

    @staticmethod
    def _assert_password_len(password):
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли пароль с сохраненным хешем."""
        return (
            User._hash_password(password, self._salt) == self._hashed_password
        )

    def update_user_db(self) -> None:
        """Сохраняет пользователя в хранилище."""
        users_info = load_json(SettingsLoader().get_db_users_path())

        for user_info in users_info:
            if user_info["user_id"] == self._user_id:
                user_info.update(self._to_dict())
                break
        else:
            users_info.append(self._to_dict())
        save_json(SettingsLoader().get_db_users_path(), users_info)

    def _to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @staticmethod
    def _hash_password(new_password, new_salt) -> str:
        """Возвращает хеш пароля с солью."""
        return hashlib.sha256(
            User._salted_pass(new_password, new_salt)
        ).hexdigest()

    @staticmethod
    def _salted_pass(password, salt) -> bytes:
        return (password + salt).encode("utf-8")


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        self._currency_code = currency_code
        self.balance = balance

    def __repr__(self) -> str:
        return (
            f"Wallet(currency_code={self._currency_code!r}, "
            f"balance={self._balance!r})"
        )

    @classmethod
    def load_wallets(cls, wallets_json) -> dict[str, Self]:
        """Создает кошельки из данных хранилища."""
        wallet_list = []
        for key, value in wallets_json.items():
            wallet_list.append(cls(key, value["balance"]))
        if not wallet_list:
            return {}
        else:
            return {wallet._currency_code: wallet for wallet in wallet_list}

    @property
    def currency_code(self) -> str:
        return self._currency_code

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, amount: float) -> None:
        Wallet._validate_number(amount)
        if amount < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(amount)

    def deposit(self, amount: float) -> None:
        """Пополняет баланс кошелька."""
        Wallet._validate_number(amount)
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Списывает сумму с баланса кошелька."""
        Wallet._validate_number(amount)
        if amount <= 0:
            raise ValueError("'amount' должен быть положительным числом")
        if self._balance >= amount:
            self.balance -= amount
        else:
            raise InsufficientFundsError(
                self._balance, amount, self._currency_code
            )

    def get_total_value(
        self, rate_info: RateInfo, base_currency: str | None = None
    ) -> float:
        """Возвращает стоимость кошелька в базовой валюте."""
        if base_currency is None:
            base_currency = SettingsLoader().get_default_base_currency()
        return rate_info.convert(
            self._balance, self._currency_code, base_currency
        )

    @staticmethod
    def _validate_number(amount) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (float, int)):
            raise TypeError("'amount' должен быть числом")
        if not math.isfinite(amount):
            raise ValueError("'amount' должен быть конечным числом")

    def get_balance_info(self) -> str:
        """Возвращает информацию о балансе кошелька."""
        return self.__str__()

    def __str__(self) -> str:
        return f"Кошелек {self._currency_code}: баланс {self._balance:.4f}"


class Portfolio:
    def __init__(
        self, user_id: int, wallets: dict[str, Wallet] | None = None
    ) -> None:
        self._user_id = user_id
        self._wallets = wallets if wallets else {}

    def __str__(self) -> str:
        return f"user_id: {self._user_id}, wallets: {self._wallets}"

    @classmethod
    def create_for_user(cls, user: User) -> Self:
        """Создает пустой портфель для пользователя."""
        return cls(user.user_id, {})

    @classmethod
    def load_portfolios(cls) -> list[Self]:
        """Загружает все портфели из хранилища."""
        portfolios_json = load_json(SettingsLoader().get_db_ports_path())
        port_list = []
        for port in portfolios_json:
            port_list.append(
                cls(port["user_id"], Wallet.load_wallets(port["wallets"]))
            )

        return port_list

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def user(self) -> User:
        users = [
            user for user in User.load_users() if user.user_id == self._user_id
        ]
        if users:
            return users[0]
        else:
            raise ValueError("Пользователь портфеля не найден")

    @property
    def wallets(self) -> dict[str, Wallet]:
        return dict(self._wallets)

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет в портфель пустой кошелек валюты."""
        if currency_code not in self._wallets:
            new_wallet = Wallet(currency_code, 0.0)
            self._wallets[currency_code] = new_wallet
            return new_wallet
        else:
            raise ValueError(f"Кошелек '{currency_code}' уже есть в портфеле")

    def get_total_value(self, base_currency: str | None = None) -> float:
        """Возвращает стоимость портфеля в базовой валюте."""
        rate_info = RateInfo.load_rate_info()
        return sum(
            (
                wallet.get_total_value(rate_info, base_currency)
                for wallet in self._wallets.values()
            ),
            0.0,
        )

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелек портфеля по коду валюты."""
        target_wallet = self._wallets.get(currency_code)
        if not target_wallet:
            raise ValueError(
                f"У вас нет кошелька '{currency_code}'. Добавьте валюту: "
                "она создается автоматически при первой покупке."
            )
        else:
            return target_wallet

    def update_portfolios_db(self) -> None:
        """Сохраняет портфель в хранилище."""
        ports_info = load_json(SettingsLoader().get_db_ports_path())

        for port_info in ports_info:
            if port_info["user_id"] == self._user_id:
                port_info.update(self._to_dict())
                break
        else:
            ports_info.append(self._to_dict())
        save_json(SettingsLoader().get_db_ports_path(), ports_info)

    def _to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "wallets": self._wallets_to_dict(),
        }

    def _wallets_to_dict(self) -> dict[str, dict]:
        wallets = {}
        for k, v in self._wallets.items():
            wallets[k] = {"balance": v.balance}

        return wallets
