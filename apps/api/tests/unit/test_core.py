import uuid

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.users.domain.password_policy import password_problems
from app.shared.text import slug_code


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("Secreta123")
    assert hashed.startswith("$argon2id$")
    assert verify_password("Secreta123", hashed)
    assert not verify_password("otra", hashed)


def test_access_token_roundtrip() -> None:
    subject = uuid.uuid4()
    token, expires_in = create_access_token(subject)
    assert expires_in == 15 * 60
    assert decode_access_token(token)["sub"] == str(subject)


def test_access_token_rejects_tampering() -> None:
    token, _ = create_access_token(uuid.uuid4())
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token[:-2] + "xx")


def test_refresh_token_is_random_and_hashed() -> None:
    a, b = generate_refresh_token(), generate_refresh_token()
    assert a != b and len(a) > 40
    assert hash_token(a) == hash_token(a) and hash_token(a) != a


@pytest.mark.parametrize(
    ("password", "ok"),
    [("Clave1234", True), ("corta1", False), ("solotexto", False), ("12345678", False)],
)
def test_password_policy(password: str, ok: bool) -> None:
    assert (password_problems(password) == []) is ok


def test_slug_code() -> None:
    assert slug_code("Visita técnica / campo") == "VISITA_TECNICA_CAMPO"
    assert slug_code("Año ñandú") == "ANO_NANDU"
