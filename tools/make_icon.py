"""Сгенерировать иконки приложения из эмблемы серии.

Эмблема — это щит героя с огоньком максимального прогресса (щит заполнен,
огонёк вырос до предела). Рисуется теми же глифами Material Symbols Rounded,
что и в приложении: `shield_rounded` + `local_fire_department_rounded`.

Запуск (нужен Pillow и fontTools, только для разработки):

    python tools/make_icon.py --font path/to/MaterialIcons-Regular.otf

Шрифт можно взять из установленного Flet:
    .venv/Lib/site-packages/flet_web/web/assets/fonts/MaterialIcons-Regular.otf

Результат:
    src/assets/icon.png     — 1024x1024, прозрачный фон (для flet build)
    src/assets/favicon.png  — 128x128, тёмная подложка (для вкладки браузера)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "assets"


def default_font() -> Path | None:
    """Шрифт иконок из установленного flet_web."""
    try:
        import flet_web
    except ImportError:
        return None
    return (
        Path(flet_web.__file__).resolve().parent
        / "web"
        / "assets"
        / "fonts"
        / "MaterialIcons-Regular.otf"
    )

#: Цвета из src/app/ui/theme.py и engine.FLAME_COLORS[0] (пик прогресса).
BG = "#080C16"
SHIELD_TOP = "#FFFFFF"
SHIELD_BOTTOM = "#D9D4FA"  # лёгкий лавандовый оттенок theme.PRIMARY
SHIELD_GLOW = "#7C5CFF"  # theme.PRIMARY
FLAME_TOP = "#FFC466"  # theme.GOLD
FLAME_BOTTOM = "#FF7A45"
FLAME = "#FF9F5A"  # engine.FLAME_COLORS[0] — цвет свечения огонька

SHIELD_GLYPH = "shield_rounded"
FLAME_GLYPH = "local_fire_department_rounded"

#: Высота щита в долях холста: эмблема занимает почти всю иконку.
SHIELD_HEIGHT = 0.78
#: Огонёк в приложении 30 px при щите 54 px.
FLAME_RATIO = 30 / 54


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def glyph_codepoint(font_path: Path, name: str) -> int:
    """Кодовая точка глифа по имени (в шрифтах Flet имена с суффиксом стиля)."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError as exc:  # pragma: no cover - dev tooling
        raise SystemExit(
            "Нужен fontTools: .venv/Scripts/python.exe -m pip install fonttools"
        ) from exc

    font = TTFont(font_path)
    for codepoint, glyph_name in font.getBestCmap().items():
        if glyph_name == name:
            return codepoint
    raise SystemExit(f"В шрифте нет глифа {name}")


def glyph_mask(font_path: Path, codepoint: int, height: int) -> Image.Image:
    """Чёрно-белая маска глифа, обрезанная по краям чернил."""
    font = ImageFont.truetype(str(font_path), height * 2)
    char = chr(codepoint)
    left, top, right, bottom = font.getbbox(char)
    canvas = Image.new("L", (right - left + 40, bottom - top + 40), 0)
    ImageDraw.Draw(canvas).text(
        (20 - left, 20 - top), char, font=font, fill=255
    )
    ink = canvas.crop(canvas.getbbox())
    width = round(ink.width * height / ink.height)
    return ink.resize((width, height), Image.LANCZOS)


def tinted(mask: Image.Image, color: str, opacity: float = 1.0) -> Image.Image:
    r, g, b = hex_rgb(color)
    alpha = mask.point(lambda value: round(value * opacity))
    layer = Image.new("RGBA", mask.size, (r, g, b, 0))
    layer.putalpha(alpha)
    return layer


def tinted_vertical(
    mask: Image.Image, top: str, bottom: str, opacity: float = 1.0
) -> Image.Image:
    """Заливка маски вертикальным градиентом."""
    start, end = hex_rgb(top), hex_rgb(bottom)
    width, height = mask.size
    gradient = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(gradient)
    for y in range(height):
        mix = y / max(1, height - 1)
        color = tuple(
            round(start[i] + (end[i] - start[i]) * mix) for i in range(3)
        )
        draw.line((0, y, width, y), fill=(*color, 255))
    gradient.putalpha(mask.point(lambda value: round(value * opacity)))
    return gradient


def glow(mask: Image.Image, color: str, blur: int, opacity: float) -> Image.Image:
    faded = mask.filter(ImageFilter.GaussianBlur(blur))
    return tinted(faded, color, opacity)


def emblem(
    font_path: Path,
    shield_codepoint: int,
    flame_codepoint: int,
    size: int,
    with_background: bool,
) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    if with_background:
        plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(plate).rounded_rectangle(
            (0, 0, size - 1, size - 1),
            radius=round(size * 0.22),
            fill=(*hex_rgb(BG), 255),
        )
        canvas = plate

    shield_h = round(size * SHIELD_HEIGHT)
    shield = glyph_mask(font_path, shield_codepoint, shield_h)
    flame_h = round(shield_h * FLAME_RATIO)
    flame = glyph_mask(font_path, flame_codepoint, flame_h)

    # Свечение щита (фиолетовое) и огонька (тёплое) — под самими глифами.
    halo_shield = glow(shield, SHIELD_GLOW, round(size * 0.055), 0.45)
    halo_flame = glow(flame, FLAME, round(size * 0.042), 0.55)

    center = (size // 2, round(size * 0.5))
    places: list[tuple[Image.Image, tuple[int, int]]] = []
    for layer, anchor in (
        (halo_shield, center),
        (tinted_vertical(shield, SHIELD_TOP, SHIELD_BOTTOM), center),
    ):
        places.append(
            (layer, (anchor[0] - layer.width // 2, anchor[1] - layer.height // 2))
        )
    places.append(
        (halo_flame, (center[0] - halo_flame.width // 2, center[1] - halo_flame.height // 2))
    )

    # Тёмный контур, чтобы огонёк читался на светлом щите (как в приложении).
    outline = flame.filter(ImageFilter.MaxFilter(17))
    outline = outline.point(lambda value: min(255, round(value * 0.9)))
    places.append(
        (
            tinted(outline, BG),
            (center[0] - outline.width // 2, center[1] - outline.height // 2),
        )
    )
    places.append(
        (
            tinted_vertical(flame, FLAME_TOP, FLAME_BOTTOM),
            (center[0] - flame.width // 2, center[1] - flame.height // 2),
        )
    )

    for layer, position in places:
        canvas.alpha_composite(layer, position)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font",
        type=Path,
        default=default_font(),
        help="MaterialIcons-Regular.otf; по умолчанию — из установленного flet_web",
    )
    args = parser.parse_args()

    font_path = args.font
    if font_path is None or not font_path.exists():
        raise SystemExit(f"Шрифт не найден: {font_path}. Укажите --font.")
    shield_codepoint = glyph_codepoint(font_path, SHIELD_GLYPH)
    flame_codepoint = glyph_codepoint(font_path, FLAME_GLYPH)

    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = emblem(
        font_path, shield_codepoint, flame_codepoint, 1024, with_background=False
    )
    icon.save(ASSETS / "icon.png")

    favicon = emblem(
        font_path, shield_codepoint, flame_codepoint, 128, with_background=True
    )
    favicon.save(ASSETS / "favicon.png")

    print(f"icon.png    {icon.size} {icon.mode}")
    print(f"favicon.png {favicon.size} {favicon.mode}")


if __name__ == "__main__":
    main()
