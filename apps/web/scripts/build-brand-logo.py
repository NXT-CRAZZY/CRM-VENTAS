"""
Genera los assets de marca (logo.png / logo-light.png) a partir del JPG original
con fondo blanco.

El logo usa solo dos colores solidos, asi que en vez de un simple "borrar blanco"
se modela cada pixel como  p = a*F + (1-a)*blanco  y se resuelve `a` para el
color de marca mas probable. Asi los bordes antialias quedan limpios (sin halo
blanco) al poner el logo sobre fondos oscuros.

Uso:
    python apps/web/scripts/build-brand-logo.py
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "DSCONT_CRM_LOGO2.jpg"
OUT_DIR = ROOT / "apps" / "web" / "src" / "assets" / "brand"
DOCS_DIR = ROOT / "docs" / "brand"

BRAND_DARK = np.array([36, 37, 40], dtype=np.float64)   # #242528
BRAND_ORANGE = np.array([224, 62, 15], dtype=np.float64)  # #E03E0F
WHITE = np.full(3, 255.0)

TARGET_WIDTH = 640
DOCS_WIDTH = 1280


def estimate_alpha(rgb: np.ndarray):
    """Devuelve (alpha, clase) modelando el pixel como mezcla con blanco.

    clase: 0 = fondo, 1 = oscuro, 2 = naranja
    """
    best_residual = np.full(rgb.shape[:2], np.inf)
    alpha = np.zeros(rgb.shape[:2])
    cls = np.zeros(rgb.shape[:2], dtype=np.uint8)

    for idx, color in ((1, BRAND_DARK), (2, BRAND_ORANGE)):
        denom = 255.0 - color
        a_channels = (255.0 - rgb) / denom
        a = np.clip(np.median(a_channels, axis=2), 0.0, 1.0)
        recon = a[..., None] * color + (1.0 - a[..., None]) * WHITE
        residual = np.mean((rgb - recon) ** 2, axis=2)

        better = residual < best_residual
        best_residual[better] = residual[better]
        alpha[better] = a[better]
        cls[better] = idx

    return alpha, cls


def clean_alpha(alpha: np.ndarray) -> np.ndarray:
    """Elimina motas aisladas del JPG y rellena micro-huecos."""
    core = alpha > 0.5

    # Quitar componentes pequenos (ruido de compresion en la zona blanca).
    labels, n = ndimage.label(core)
    if n:
        sizes = ndimage.sum(core, labels, range(1, n + 1))
        keep = np.zeros(n + 1, dtype=bool)
        keep[1:] = sizes >= 120
        core = keep[labels]

    # Rellenar huecos diminutos del interior (el hueco grande de la "S" se conserva).
    holes = ~core
    h_labels, h_n = ndimage.label(holes)
    if h_n:
        h_sizes = ndimage.sum(holes, h_labels, range(1, h_n + 1))
        fill = np.zeros(h_n + 1, dtype=bool)
        fill[1:] = h_sizes < 120
        alpha[fill[h_labels]] = 1.0

    # Conservar el borde antialias alrededor de las formas solidas.
    near = ndimage.binary_dilation(core, iterations=4)
    return np.where(near, alpha, 0.0)


def build_rgba(rgb: np.ndarray, alpha: np.ndarray, cls: np.ndarray) -> Image.Image:
    out = np.zeros((*rgb.shape[:2], 4), dtype=np.float64)
    out[..., :3] = np.where(cls[..., None] == 1, BRAND_DARK, BRAND_ORANGE)
    # En el interior solido se conserva el color original (mezclas naranja/oscuro).
    interior = alpha >= 0.95
    out[interior, :3] = rgb[interior]
    out[..., 3] = alpha * 255.0
    return Image.fromarray(np.round(np.clip(out, 0, 255)).astype(np.uint8), "RGBA")


def resize_premultiplied(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    arr = np.asarray(im, dtype=np.float64) / 255.0
    a = arr[..., 3:4]
    prem = arr[..., :3] * a

    rgb_img = Image.fromarray(np.round(np.clip(prem * 255, 0, 255)).astype(np.uint8), "RGB")
    a_img = Image.fromarray(np.round(a[..., 0] * 255).astype(np.uint8), "L")

    rgb_r = np.asarray(rgb_img.resize(size, Image.LANCZOS), dtype=np.float64) / 255.0
    a_r = np.asarray(a_img.resize(size, Image.LANCZOS), dtype=np.float64) / 255.0

    safe_a = np.maximum(a_r, 1e-6)[..., None]
    rgb_out = np.where(a_r[..., None] > 1e-6, rgb_r / safe_a, 0.0)
    out = np.dstack([np.clip(rgb_out, 0, 1), a_r]) * 255.0
    return Image.fromarray(np.round(np.clip(out, 0, 255)).astype(np.uint8), "RGBA")


def trim(im: Image.Image, pad: int = 2) -> Image.Image:
    bbox = im.getchannel("A").point(lambda v: 255 if v > 4 else 0).getbbox()
    if not bbox:
        return im
    left, top, right, bottom = bbox
    left, top = max(0, left - pad), max(0, top - pad)
    right, bottom = min(im.width, right + pad), min(im.height, bottom + pad)
    return im.crop((left, top, right, bottom))


def light_variant(im: Image.Image) -> Image.Image:
    """Version para fondos oscuros: las partes oscuras pasan a blanco."""
    arr = np.asarray(im, dtype=np.float64).copy()
    rgb, a = arr[..., :3], arr[..., 3]
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722])
    dark = (lum < 120) & (a > 0)
    rgb[dark] = 255.0
    arr[..., :3] = rgb
    return Image.fromarray(np.round(np.clip(arr, 0, 255)).astype(np.uint8), "RGBA")


def main() -> None:
    src = Image.open(SRC).convert("RGB")
    rgb = np.asarray(src, dtype=np.float64)

    alpha, cls = estimate_alpha(rgb)
    alpha = np.clip(clean_alpha(alpha), 0.0, 1.0)

    master = trim(build_rgba(rgb, alpha, cls))

    logo = resize_premultiplied(master, (TARGET_WIDTH, round(master.height * TARGET_WIDTH / master.width)))
    logo = trim(logo)
    logo.save(OUT_DIR / "logo.png", optimize=True)

    light = light_variant(logo)
    light.save(OUT_DIR / "logo-light.png", optimize=True)

    # Copia de alta resolucion para el manual / docs.
    docs = resize_premultiplied(master, (DOCS_WIDTH, round(master.height * DOCS_WIDTH / master.width)))
    docs.save(DOCS_DIR / "DSCONT_CRM.png", optimize=True)
    docs.save(ROOT / "DSCONT_CRM.png", optimize=True)

    print("logo.png       ", logo.size)
    print("logo-light.png ", light.size)
    print("DSCONT_CRM.png ", docs.size)


if __name__ == "__main__":
    main()
