"""Validación de documentos de identidad peruanos (DNI y RUC).

Se usa desde la fase 0 (datos sintéticos) y será la base de la validación de prospectos (fase 2).
"""

import re

_RUC_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
_RUC_PREFIXES = ("10", "15", "17", "20")


def ruc_check_digit(first_ten: str) -> int:
    """Dígito verificador SUNAT (módulo 11) para los 10 primeros dígitos del RUC."""
    total = sum(int(d) * w for d, w in zip(first_ten, _RUC_WEIGHTS, strict=True))
    result = 11 - (total % 11)
    return {10: 0, 11: 1}.get(result, result)


def is_valid_ruc(ruc: str) -> bool:
    if not re.fullmatch(r"\d{11}", ruc or "") or ruc[:2] not in _RUC_PREFIXES:
        return False
    return ruc_check_digit(ruc[:10]) == int(ruc[10])


def is_valid_dni(dni: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", dni or ""))


def ruc_person_type(ruc: str) -> str | None:
    """RUC 10/15/17 = persona natural con negocio; 20 = persona jurídica."""
    if not is_valid_ruc(ruc):
        return None
    return "JURIDICA" if ruc.startswith("20") else "NATURAL"
