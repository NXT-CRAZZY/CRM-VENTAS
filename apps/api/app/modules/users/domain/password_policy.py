import re

MIN_LENGTH = 8


def password_problems(password: str) -> list[str]:
    """Reglas simples y explicables para usuarios no técnicos."""
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"Debe tener al menos {MIN_LENGTH} caracteres.")
    if not re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", password):
        problems.append("Debe incluir al menos una letra.")
    if not re.search(r"\d", password):
        problems.append("Debe incluir al menos un número.")
    return problems


def validate_password(password: str) -> str:
    problems = password_problems(password)
    if problems:
        raise ValueError(" ".join(problems))
    return password
