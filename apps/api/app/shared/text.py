import re
import unicodedata


def slug_code(text: str, max_len: int = 40) -> str:
    """'Visita técnica' -> 'VISITA_TECNICA'."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", ascii_text.upper()).strip("_")[:max_len]


HEX_COLOR = r"^#[0-9A-Fa-f]{6}$"
