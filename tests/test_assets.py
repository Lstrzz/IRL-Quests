"""Ассеты, которые нужны `flet build`: иконка приложения и favicon."""

from pathlib import Path

from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "src" / "assets"


def test_app_icon_is_square_and_transparent() -> None:
    with Image.open(ASSETS / "icon.png") as icon:
        assert icon.size == (1024, 1024)
        assert icon.mode == "RGBA"

        alpha = icon.getchannel("A")
        assert alpha.getextrema() == (0, 255)

        left, top, right, bottom = icon.getbbox()
        assert right - left >= 512
        assert bottom - top >= 640


def test_favicon_has_dark_background() -> None:
    with Image.open(ASSETS / "favicon.png") as favicon:
        assert favicon.size == (128, 128)
        assert favicon.getchannel("A").getextrema() == (0, 255)
        assert favicon.convert("RGB").getpixel((64, 8)) == (8, 12, 22)
