"""Скриншоты эмблемы серии за каждый месяц прогрессии.

Скрипт рисует эмблему теми же глифами и по тем же формулам, что и приложение
(`engine.shield_opacity`, `engine.flame_progress`, `engine.flame_color`), и
сохраняет по одному PNG на месяц:

    screenshots/streak_months/month_00_start.png   — 0 дней, щит 25%
    screenshots/streak_months/month_01_30d.png     — щит полностью проявился
    screenshots/streak_months/month_02_60d.png     — огонёк вырос до максимума
    screenshots/streak_months/month_03_90d.png     — первый цвет огонька
    ...
    screenshots/streak_months/month_14_420d.png    — цикл цветов замкнулся

Плюс общий лист `all_months.png`.

Запуск (нужны Pillow и fontTools):

    python tools/make_streak_gallery.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from app import engine  # noqa: E402
from make_icon import (  # noqa: E402
    BG,
    FLAME_GLYPH,
    SHIELD_BOTTOM,
    SHIELD_GLYPH,
    SHIELD_GLOW,
    SHIELD_TOP,
    default_font,
    glyph_codepoint,
    glyph_mask,
    hex_rgb,
    tinted,
    tinted_vertical,
)

OUT_DIR = ROOT / "screenshots" / "streak_months"

TEXT = "#EEF2FF"
MUTED = "#8B97B5"
SURFACE = "#121A2B"

CARD_W = 640
CARD_H = 720
SHIELD_H = 300
EMBLEM_Y = 278
#: В приложении щит 54 px, огонёк 10–30 px — сохраняем эти пропорции.
UI_SHIELD = 54
UI_FLAME_MIN = 10
UI_FLAME_MAX = 30

MONTH_DAYS = 30
#: Старт + 14 месяцев: месяц 14 — цвет вернулся к первому.
MONTHS = 14


def label_fonts() -> tuple[Path, Path]:
    """Обычный и жирный шрифт с кириллицей для подписей."""
    candidates = [
        (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            return regular, bold
    raise SystemExit("Не найден шрифт с кириллицей для подписей")


def shadow(mask: Image.Image, color: str, blur: int, opacity: float) -> Image.Image:
    """Размытая цветная тень под глифом (аналог BoxShadow)."""
    return tinted(mask.filter(ImageFilter.GaussianBlur(max(1, blur))), color, opacity)


def paste_center(
    canvas: Image.Image, layer: Image.Image, center: tuple[int, int]
) -> None:
    canvas.alpha_composite(
        layer, (center[0] - layer.width // 2, center[1] - layer.height // 2)
    )


def render_emblem(
    font_path: Path,
    shield_codepoint: int,
    flame_codepoint: int,
    streak: int,
    size: tuple[int, int],
    center: tuple[int, int],
    shield_h: int,
) -> Image.Image:
    """Эмблема в состоянии серии `streak` на прозрачном холсте."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))

    shield_alpha = engine.shield_opacity(streak)
    shield_progress = max(0.0, min(1.0, (shield_alpha - 0.25) / 0.75))
    flame = engine.flame_progress(streak)
    flame_color = engine.flame_color(streak)

    # Все размеры теней в UI заданы для щита 54 px — масштабируем.
    scale = shield_h / UI_SHIELD

    shield = glyph_mask(font_path, shield_codepoint, shield_h)
    paste_center(
        layer,
        shadow(
            shield,
            SHIELD_GLOW,
            round((8 + 16 * shield_progress) * scale),
            0.10 + 0.25 * shield_progress,
        ),
        center,
    )
    paste_center(
        layer,
        tinted_vertical(shield, SHIELD_TOP, SHIELD_BOTTOM, shield_alpha),
        center,
    )

    if flame <= 0:
        return layer

    flame_h = round(shield_h * (UI_FLAME_MIN + 20 * flame) / UI_SHIELD)
    flame_mask = glyph_mask(font_path, flame_codepoint, flame_h)
    flame_alpha = 0.35 + 0.65 * flame

    paste_center(
        layer,
        shadow(
            flame_mask,
            flame_color,
            round((4 + 12 * flame) * scale),
            0.35 * flame,
        ),
        center,
    )
    # Тёмный контур, чтобы огонёк читался на светлом щите.
    outline = flame_mask.filter(ImageFilter.MaxFilter(13))
    outline = outline.filter(ImageFilter.GaussianBlur(1))
    paste_center(layer, tinted(outline, BG, 0.55), center)
    paste_center(layer, tinted(flame_mask, flame_color, flame_alpha), center)
    return layer


def month_caption(month: int, streak: int) -> tuple[str, str]:
    """Заголовок и пояснение под эмблемой."""
    if month == 0:
        return "Старт", "щит проявился на 25%"
    if month == 1:
        return "Месяц 1", "щит полностью проявился"
    if month == 2:
        return "Месяц 2", "огонёк вырос до максимума"
    color = engine.flame_color(streak)
    if month == MONTHS:
        return f"Месяц {month}", f"цвет {color} · цикл начинается заново"
    return f"Месяц {month}", f"цвет огонька {color}"


def render_card(
    font_path: Path,
    shield_codepoint: int,
    flame_codepoint: int,
    regular: Path,
    bold: Path,
    month: int,
) -> Image.Image:
    streak = month * MONTH_DAYS
    card = Image.new("RGBA", (CARD_W, CARD_H), (*hex_rgb(BG), 255))
    emblem = render_emblem(
        font_path,
        shield_codepoint,
        flame_codepoint,
        streak,
        (CARD_W, CARD_H),
        (CARD_W // 2, EMBLEM_Y),
        SHIELD_H,
    )
    card.alpha_composite(emblem)

    draw = ImageDraw.Draw(card)
    title_font = ImageFont.truetype(str(bold), 40)
    body_font = ImageFont.truetype(str(regular), 24)
    foot_font = ImageFont.truetype(str(regular), 16)

    title, note = month_caption(month, streak)
    draw.text((CARD_W // 2, 520), title, font=title_font, fill=TEXT, anchor="mm")
    draw.text(
        (CARD_W // 2, 566),
        f"{streak} дней серии",
        font=body_font,
        fill=MUTED,
        anchor="mm",
    )

    if month >= 3:
        color = engine.flame_color(streak)
        text_x = CARD_W // 2 + 8
        draw.text(
            (text_x, 606), note, font=body_font, fill=TEXT, anchor="lm"
        )
        bbox = draw.textbbox((text_x, 606), note, font=body_font, anchor="lm")
        chip = (bbox[0] - 18, 606)
        draw.ellipse(
            (chip[0] - 7, chip[1] - 7, chip[0] + 7, chip[1] + 7),
            fill=color,
            outline=TEXT,
            width=1,
        )
    else:
        draw.text(
            (CARD_W // 2, 606), note, font=body_font, fill=TEXT, anchor="mm"
        )

    draw.text(
        (CARD_W // 2, 688),
        "IRL Quests · эмблема серии",
        font=foot_font,
        fill=MUTED,
        anchor="mm",
    )
    return card


def contact_sheet(cards: list[Image.Image], bold: Path) -> Image.Image:
    """Общий лист: все месяцы сеткой 5×3."""
    columns, gap, header = 5, 18, 90
    tile_w, tile_h = 300, 338
    rows = (len(cards) + columns - 1) // columns
    width = columns * tile_w + (columns + 1) * gap
    height = header + rows * tile_h + (rows + 1) * gap
    sheet = Image.new("RGBA", (width, height), (*hex_rgb(BG), 255))
    draw = ImageDraw.Draw(sheet)
    title_font = ImageFont.truetype(str(bold), 34)
    draw.text(
        (width // 2, 44),
        "Прогрессия серии: эмблема по месяцам",
        font=title_font,
        fill=TEXT,
        anchor="mm",
    )

    for index, card in enumerate(cards):
        row, column = divmod(index, columns)
        x = gap + column * (tile_w + gap)
        y = header + gap + row * (tile_h + gap)
        sheet.alpha_composite(
            card.resize((tile_w, tile_h), Image.LANCZOS), (x, y)
        )
    return sheet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--font",
        type=Path,
        default=default_font(),
        help="MaterialIcons-Regular.otf; по умолчанию — из установленного flet_web",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DIR,
        help="папка для скриншотов",
    )
    args = parser.parse_args()

    font_path = args.font
    if font_path is None or not font_path.exists():
        raise SystemExit(f"Шрифт не найден: {font_path}. Укажите --font.")
    shield_codepoint = glyph_codepoint(font_path, SHIELD_GLYPH)
    flame_codepoint = glyph_codepoint(font_path, FLAME_GLYPH)
    regular, bold = label_fonts()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    cards: list[Image.Image] = []
    for month in range(MONTHS + 1):
        streak = month * MONTH_DAYS
        card = render_card(
            font_path,
            shield_codepoint,
            flame_codepoint,
            regular,
            bold,
            month,
        )
        if month == 0:
            name = "month_00_start.png"
        else:
            name = f"month_{month:02d}_{streak:03d}d.png"
        card.save(out_dir / name)
        cards.append(card)
        print(
            f"{name:<24} серия {streak:>3} дн. · "
            f"щит {engine.shield_opacity(streak) * 100:>3.0f}% · "
            f"огонёк {engine.flame_progress(streak) * 100:>3.0f}% · "
            f"{engine.flame_color(streak)}"
        )

    sheet = contact_sheet(cards, bold)
    sheet.save(out_dir / "all_months.png")
    print(f"all_months.png          {sheet.width}×{sheet.height}")


if __name__ == "__main__":
    main()
