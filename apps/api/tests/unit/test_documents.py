import pytest

from app.shared.documents import is_valid_dni, is_valid_ruc, ruc_check_digit, ruc_person_type


def test_ruc_check_digit_known_value() -> None:
    # RUC público de SUNAT: 20131312955
    assert ruc_check_digit("2013131295") == 5
    assert is_valid_ruc("20131312955")


@pytest.mark.parametrize("ruc", ["20131312954", "2013131295", "30131312955", "2013131295X", ""])
def test_invalid_rucs(ruc: str) -> None:
    assert not is_valid_ruc(ruc)


def test_ruc_person_type() -> None:
    natural = "1046123456" + str(ruc_check_digit("1046123456"))
    assert ruc_person_type(natural) == "NATURAL"
    assert ruc_person_type("20131312955") == "JURIDICA"
    assert ruc_person_type("123") is None


@pytest.mark.parametrize(("dni", "ok"), [("45678912", True), ("4567891", False), ("4567891A", False)])
def test_dni(dni: str, ok: bool) -> None:
    assert is_valid_dni(dni) is ok
