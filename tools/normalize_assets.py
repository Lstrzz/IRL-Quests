"""Привести пользовательские иконки к размерам, которые ждёт `flet build`.

Скрипт не рисует иконки заново, а только масштабирует уже лежащие в
`src/assets` изображения:

    icon.png    — 1024x1024, прозрачный фон;
    favicon.png — 128x128, тёмная подложка #080C16.

Оригиналы сохраняются в `assets_backup/` и при повторном запуске не
перезаписываются. Повторный запуск безопасен: уже нормализованные файлы
пропускаются. Запуск:

    .venv/Scripts/python.exe tools/normalize_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "assets"
BACKUP = ROOT / "assets_backup"

ICON_SIZE = 1024
#: Высота эмблемы на прозрачном холсте. Даёт bbox заметно больше 512x640.
ICON_ART_HEIGHT = 820

FAVICON_SIZE = 128
#: Художественная часть favicon; поля вокруг нужны для тёмной подложки.
FAVICON_ART_SIZE = 104
FAVICON_RADIUS = 26

BG_RGB = (8, 12, 22)  # theme.BG


def backup(path: Path) -> None:
    """Сохранить исходник, не затирая более раннюю резервную копию."""
    BACKUP.mkdir(parents=True, exist_ok=True)
    target = BACKUP / path.name
    if not target.exists():
        target.write_bytes(path.read_bytes())


def icon_is_normalized(image: Image.Image) -> bool:
    if image.size != (ICON_SIZE, ICON_SIZE) or image.mode != "RGBA":
        return False
    bbox = image.getbbox()
    if not bbox:
        return False
    left, top, right, bottom = bbox
    # Нормализованная эмблема вписана в холст по одной из сторон и стоит по центру.
    if max(right - left, bottom - top) not in (ICON_ART_HEIGHT, ICON_SIZE):
        return False
    return (
        abs(left - (ICON_SIZE - right)) <= 1
        and abs(top - (ICON_SIZE - bottom)) <= 1
    )


def favicon_is_normalized(image: Image.Image) -> bool:
    if image.size != (FAVICON_SIZE, FAVICON_SIZE) or image.mode != "RGBA":
        return False
    if image.getchannel("A").getextrema() != (0, 255):
        return False
    return image.convert("RGB").getpixel((64, 8)) == BG_RGB


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Вписать изображение в рамку с сохранением пропорций."""
    scale = min(size[0] / image.width, size[1] / image.height)
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.LANCZOS,
    )


def normalized_icon(source: Image.Image) -> Image.Image:
    source = source.convert("RGBA")
    bbox = source.getbbox() or (0, 0, source.width, source.height)
    art = fit(
        source.crop(bbox),
        (ICON_SIZE, ICON_ART_HEIGHT),
    )
    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(
        art,
        (
            (ICON_SIZE - art.width) // 2,
            (ICON_SIZE - art.height) // 2,
        ),
    )
    return canvas


def normalized_favicon(source: Image.Image) -> Image.Image:
    source = source.convert("RGBA")
    bbox = source.getbbox() or (0, 0, source.width, source.height)
    art = fit(
        source.crop(bbox),
        (FAVICON_ART_SIZE, FAVICON_ART_SIZE),
    )

    plate = Image.new("RGBA", (FAVICON_SIZE, FAVICON_SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        (0, 0, FAVICON_SIZE - 1, FAVICON_SIZE - 1),
        radius=FAVICON_RADIUS,
        fill=(*BG_RGB, 255),
    )
    plate.alpha_composite(
        art,
        (
            (FAVICON_SIZE - art.width) // 2,
            (FAVICON_SIZE - art.height) // 2,
        ),
    )

    # Даже если исходник непрозрачный, углы favicon остаются прозрачными.
    mask = Image.new("L", (FAVICON_SIZE, FAVICON_SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, FAVICON_SIZE - 1, FAVICON_SIZE - 1),
        radius=FAVICON_RADIUS,
        fill=255,
    )
    plate.putalpha(ImageChops.multiply(plate.getchannel("A"), mask))
    return plate


def main() -> None:
    icon_path = ASSETS / "icon.png"
    favicon_path = ASSETS / "favicon.png"

    icon_source = Image.open(icon_path)
    if icon_is_normalized(icon_source):
        print(f"icon.png    {icon_source.size} уже нормализован")
        icon = icon_source
    else:
        backup(icon_path)
        icon = normalized_icon(icon_source)
        icon.save(icon_path)

    favicon_source = Image.open(favicon_path)
    if favicon_is_normalized(favicon_source):
        print(f"favicon.png {favicon_source.size} уже нормализован")
        favicon = favicon_source
    else:
        backup(favicon_path)
        favicon = normalized_favicon(favicon_source)
        favicon.save(favicon_path)

    print(f"icon.png    {icon.size} {icon.mode} bbox={icon.getbbox()}")
    print(f"favicon.png {favicon.size} {favicon.mode}")
    print(f"резервные копии: {BACKUP}")


if __name__ == "__main__":
    main()
