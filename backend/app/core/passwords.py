from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.errors import ValidationError

_password_hasher = PasswordHash.recommended()
_dummy_hash = _password_hasher.hash("ledgerchain-invalid-login-sentinel")


class PasswordService:
    minimum_length = 10
    maximum_length = 128

    @classmethod
    def validate(cls, password: str) -> None:
        if len(password) < cls.minimum_length or len(password) > cls.maximum_length:
            raise ValidationError(
                f"Password must be between {cls.minimum_length} and {cls.maximum_length} characters.",
                code="INVALID_PASSWORD",
            )
        if len(password.encode("utf-8")) > 1024:
            raise ValidationError("Password is too long.", code="INVALID_PASSWORD")
        mixed_case = any(character.islower() for character in password) and any(
            character.isupper() for character in password
        )
        has_number = any(character.isdigit() for character in password)
        has_symbol = any(not character.isalnum() for character in password)
        if sum((mixed_case, has_number, has_symbol)) < 2:
            raise ValidationError(
                "Password must include at least two of mixed case, a number, and a symbol.",
                code="INVALID_PASSWORD",
            )

    @staticmethod
    def hash(password: str) -> str:
        return _password_hasher.hash(password)

    @staticmethod
    def verify(password: str, password_hash: str | None) -> bool:
        try:
            valid = _password_hasher.verify(password, password_hash or _dummy_hash)
        except UnknownHashError:
            return False
        return valid and password_hash is not None
