"""Точка входа приложения IRL Quests.

Локальный запуск:
    flet run src/main.py

Сборка Android APK:
    flet build apk
"""

from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

from app.ui.app import IRLApp


def _icon_path() -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / "assets" / "icon.ico")


def main(page: ft.Page) -> None:
    window = page.window
    window.width = 420
    window.height = 800
    window.min_width = 360
    window.min_height = 640
    window.icon = _icon_path()
    IRLApp(page).mount()


if __name__ == "__main__":
    # assets_dir=None — приложению пока не нужны внешние ресурсы.
    ft.run(main, assets_dir=None)
