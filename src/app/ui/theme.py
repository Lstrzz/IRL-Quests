"""Палитра, иконки и переиспользуемые визуальные примитивы."""

from __future__ import annotations

from typing import Callable

import flet as ft

# ---------------------------------------------------------------------------
# Палитра
# ---------------------------------------------------------------------------

BG = "#080C16"
SURFACE = "#121A2B"
SURFACE_2 = "#1A2438"
BORDER = "#243149"

PRIMARY = "#7C5CFF"
PRIMARY_DARK = "#4B3AA8"
ACCENT = "#3DE1B0"
CYAN = "#4CC9F0"
GOLD = "#FFC466"
ORANGE = "#FF9F5A"
PINK = "#FF6B9D"
DANGER = "#FF6B81"

TEXT = "#EEF2FF"
MUTED = "#8B97B5"
DIM = "#5D6A85"

DIFFICULTY_COLORS = {
    "easy": ACCENT,
    "normal": CYAN,
    "hard": ORANGE,
    "epic": PINK,
}

ATTR_META = {
    "strength": ("fitness_center", "#FF8A65"),
    "intellect": ("psychology", CYAN),
    "will": ("shield", "#B39DDB"),
    "charisma": ("favorite", PINK),
}

QUOTES = [
    "Маленькие шаги каждый день побеждают большие рывки раз в месяц.",
    "Ты не поднимаешься до уровня своих целей — ты опускаешься до уровня своих привычек.",
    "Дисциплина — это выбор между тем, что хочется сейчас, и тем, что важно потом.",
    "Прогресс важнее совершенства.",
    "Один выполненный квест лучше десяти запланированных.",
    "Сегодняшний ты — соперник вчерашнего. Победи его.",
    "Усталость проходит, результат остаётся.",
]


def icon(name: str, fallback: ft.IconData = ft.Icons.STAR_ROUNDED) -> ft.IconData:
    """Иконка по строковому имени из модели данных."""
    return getattr(ft.Icons, name.upper(), fallback)


def attr_color(code: str) -> str:
    return ATTR_META.get(code, ("", PRIMARY))[1]


def attr_icon(code: str) -> ft.IconData:
    return icon(ATTR_META.get(code, ("star", ""))[0])


# ---------------------------------------------------------------------------
# Тёмные поверхности: диалоги, меню, выпадающие списки
# ---------------------------------------------------------------------------

DIALOG_RADIUS = 26
MENU_RADIUS = 16

#: Прозрачность фиолетовой тени у окон. Должна быть еле заметной.
WINDOW_GLOW = 0.10


def menu_style(elevation: int = 12) -> ft.MenuStyle:
    """Тёмное меню с едва заметным фиолетовым свечением."""
    return ft.MenuStyle(
        bgcolor=SURFACE,
        shadow_color=ft.Colors.with_opacity(WINDOW_GLOW, PRIMARY),
        elevation=elevation,
        padding=ft.Padding.symmetric(horizontal=6, vertical=6),
        shape=ft.RoundedRectangleBorder(
            radius=MENU_RADIUS + 2,
            side=ft.BorderSide(1, BORDER),
        ),
    )


def menu_item_style(color: str = TEXT) -> ft.ButtonStyle:
    """Пункт меню или опция выпадающего списка."""
    return ft.ButtonStyle(
        color=color,
        bgcolor=SURFACE,
        overlay_color=ft.Colors.with_opacity(0.10, PRIMARY),
        padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        shape=ft.RoundedRectangleBorder(radius=10),
        text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
    )


def dialog_badge(icon_data: ft.IconData, color: str = PRIMARY) -> ft.Container:
    """Иконка диалога в подсвеченной скруглённой плашке."""
    return ft.Container(
        content=ft.Icon(icon_data, size=26, color=color),
        width=54,
        height=54,
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.with_opacity(0.14, color),
        border=ft.Border.all(1, ft.Colors.with_opacity(0.34, color)),
        border_radius=18,
        shadow=ft.BoxShadow(
            blur_radius=22,
            color=ft.Colors.with_opacity(0.20, color),
        ),
    )


def dialog_theme() -> ft.DialogTheme:
    return ft.DialogTheme(
        bgcolor=SURFACE,
        shadow_color=ft.Colors.with_opacity(WINDOW_GLOW, PRIMARY),
        icon_color=PRIMARY,
        elevation=20,
        shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
        title_text_style=ft.TextStyle(
            size=19, weight=ft.FontWeight.BOLD, color=TEXT
        ),
        content_text_style=ft.TextStyle(size=13, color=MUTED),
        barrier_color=ft.Colors.with_opacity(0.68, BG),
        inset_padding=ft.Padding.symmetric(horizontal=20, vertical=24),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def dropdown_theme() -> ft.DropdownTheme:
    return ft.DropdownTheme(
        menu_style=menu_style(),
        text_style=ft.TextStyle(size=15, color=TEXT),
    )


def popup_menu_theme() -> ft.PopupMenuTheme:
    return ft.PopupMenuTheme(
        color=TEXT,
        shadow_color=ft.Colors.with_opacity(WINDOW_GLOW, PRIMARY),
        icon_color=MUTED,
        label_text_style=ft.TextStyle(
            size=13, color=TEXT, weight=ft.FontWeight.W_500
        ),
        elevation=10,
        shape=ft.RoundedRectangleBorder(
            radius=MENU_RADIUS,
            side=ft.BorderSide(1, BORDER),
        ),
        menu_padding=ft.Padding.symmetric(horizontal=6, vertical=6),
    )


def snackbar_theme() -> ft.SnackBarTheme:
    return ft.SnackBarTheme(
        bgcolor=SURFACE_2,
        elevation=10,
        shape=ft.RoundedRectangleBorder(radius=14),
        content_text_style=ft.TextStyle(size=13, color=TEXT),
        behavior=ft.SnackBarBehavior.FLOATING,
    )


# ---------------------------------------------------------------------------
# Примитивы
# ---------------------------------------------------------------------------


def panel(
    content: ft.Control,
    *,
    padding: int | ft.Padding = 16,
    bgcolor: str | None = SURFACE,
    gradient: ft.Gradient | None = None,
    border: bool = True,
    border_color: str | None = None,
    shadow: ft.BoxShadow | None = None,
    radius: int = 20,
    expand: bool | int | None = None,
    on_click: Callable | None = None,
    ink: bool = False,
) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=bgcolor,
        gradient=gradient,
        border=ft.Border.all(1, border_color or BORDER) if border else None,
        border_radius=radius,
        shadow=shadow,
        expand=expand,
        on_click=on_click,
        ink=ink,
    )


def pill(
    text: str,
    *,
    icon_data: ft.IconData | None = None,
    color: str = GOLD,
    bgcolor: str | None = None,
    size: int = 12,
) -> ft.Container:
    controls: list[ft.Control] = []
    if icon_data is not None:
        controls.append(ft.Icon(icon_data, size=14, color=color))
    controls.append(ft.Text(text, size=size, color=color, weight=ft.FontWeight.W_600))
    return ft.Container(
        content=ft.Row(controls, spacing=4, tight=True),
        padding=ft.Padding.symmetric(horizontal=9, vertical=5),
        bgcolor=bgcolor or ft.Colors.with_opacity(0.12, color),
        border_radius=10,
    )


def section_header(
    title: str,
    *,
    subtitle: str | None = None,
    action: str | None = None,
    on_action: Callable | None = None,
    action_icon: ft.IconData = ft.Icons.ADD_ROUNDED,
) -> ft.Row:
    left: list[ft.Control] = [
        ft.Column(
            controls=[
                ft.Text(title, size=17, weight=ft.FontWeight.BOLD, color=TEXT),
                *(
                    [ft.Text(subtitle, size=12, color=MUTED)]
                    if subtitle
                    else []
                ),
            ],
            spacing=1,
            tight=True,
        )
    ]
    right: list[ft.Control] = []
    if action and on_action:
        right.append(
            ft.TextButton(
                content=ft.Row(
                    [
                        ft.Text(action, size=12, color=ACCENT),
                        ft.Icon(action_icon, size=15, color=ACCENT),
                    ],
                    spacing=2,
                    tight=True,
                ),
                on_click=lambda e: on_action(),
            )
        )
    return ft.Row(
        controls=[*left, ft.Container(expand=True), *right],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def progress_bar(value: float, color: str = ACCENT, height: int = 8) -> ft.ProgressBar:
    return ft.ProgressBar(
        value=max(0.0, min(1.0, value)),
        color=color,
        bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
        bar_height=height,
        border_radius=height,
    )


def stat_tile(
    value: str,
    label: str,
    *,
    icon_data: ft.IconData | None = None,
    color: str = TEXT,
) -> ft.Container:
    row: list[ft.Control] = []
    if icon_data is not None:
        row.append(ft.Icon(icon_data, size=16, color=color))
    row.append(ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=color))
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(row, spacing=5, tight=True, alignment=ft.MainAxisAlignment.CENTER),
                ft.Text(label, size=11, color=MUTED, text_align=ft.TextAlign.CENTER),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
    )


def text_field(
    label: str,
    *,
    hint: str = "",
    value: str = "",
    multiline: bool = False,
    keyboard_type: ft.KeyboardType = ft.KeyboardType.TEXT,
) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        value=value,
        multiline=multiline,
        min_lines=2 if multiline else None,
        max_lines=4 if multiline else None,
        keyboard_type=keyboard_type,
        filled=True,
        fill_color=SURFACE_2,
        border_color=BORDER,
        border_width=1,
        focused_border_color=PRIMARY,
        focused_border_width=1.5,
        border_radius=14,
        color=TEXT,
        cursor_color=ACCENT,
        label_style=ft.TextStyle(color=MUTED, size=13),
        hint_style=ft.TextStyle(color=DIM, size=13),
        text_size=15,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=14),
    )


def dropdown(
    label: str,
    options: list[tuple[str, str]],
    *,
    value: str | None = None,
) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        options=[
            ft.DropdownOption(
                key=key,
                text=text,
                style=menu_item_style(),
            )
            for key, text in options
        ],
        filled=True,
        fill_color=SURFACE_2,
        border_color=BORDER,
        border_width=1,
        focused_border_color=PRIMARY,
        focused_border_width=1.5,
        border_radius=14,
        color=TEXT,
        hover_color=ft.Colors.with_opacity(0.05, PRIMARY),
        text_style=ft.TextStyle(size=15, color=TEXT),
        text_size=15,
        label_style=ft.TextStyle(color=MUTED, size=13),
        hint_style=ft.TextStyle(color=DIM, size=13),
        error_style=ft.TextStyle(color=DANGER, size=11),
        trailing_icon=ft.Icon(
            ft.Icons.EXPAND_MORE_ROUNDED, size=20, color=MUTED
        ),
        selected_trailing_icon=ft.Icon(
            ft.Icons.EXPAND_MORE_ROUNDED, size=20, color=PRIMARY
        ),
        menu_style=menu_style(),
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=8),
    )


def primary_button(
    text: str,
    on_click: Callable,
    *,
    icon_data: ft.IconData | None = None,
    color: str = ACCENT,
    expand: bool = False,
) -> ft.Button:
    return ft.Button(
        content=text,
        icon=icon_data,
        icon_color=BG,
        color=BG,
        bgcolor=color,
        expand=expand,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.BOLD),
        ),
        on_click=lambda e: on_click(),
    )


def ghost_button(
    text: str,
    on_click: Callable,
    *,
    color: str = MUTED,
    expand: bool = False,
) -> ft.TextButton:
    return ft.TextButton(
        content=text,
        expand=expand,
        style=ft.ButtonStyle(
            color=color,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        ),
        on_click=lambda e: on_click(),
    )


def round_add(on_click: Callable, tooltip: str = "Добавить") -> ft.IconButton:
    return ft.IconButton(
        icon=ft.Icons.ADD_ROUNDED,
        icon_color=BG,
        icon_size=22,
        bgcolor=ACCENT,
        width=42,
        height=42,
        tooltip=tooltip,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=13),
            padding=0,
        ),
        on_click=lambda e: on_click(),
    )


def dialog_shell(
    title: str,
    content: ft.Control,
    actions: list[ft.Control],
    *,
    icon_data: ft.IconData | None = None,
    icon_color: str = PRIMARY,
) -> ft.AlertDialog:
    return ft.AlertDialog(
        modal=True,
        bgcolor=SURFACE,
        elevation=20,
        shadow_color=ft.Colors.with_opacity(WINDOW_GLOW, PRIMARY),
        barrier_color=ft.Colors.with_opacity(0.68, BG),
        shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
        icon=(
            ft.Row(
                [dialog_badge(icon_data, icon_color)],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True,
            )
            if icon_data
            else None
        ),
        icon_padding=ft.Padding.only(top=22),
        title=ft.Text(title, size=19, weight=ft.FontWeight.BOLD, color=TEXT),
        title_padding=ft.Padding.only(left=24, right=24, top=12),
        content=ft.Container(content=content, padding=ft.Padding.only(top=8)),
        content_padding=ft.Padding.only(left=24, right=24, top=4, bottom=2),
        actions=actions,
        actions_padding=ft.Padding.only(left=20, right=20, top=12, bottom=18),
        actions_alignment=ft.MainAxisAlignment.END,
        inset_padding=ft.Padding.symmetric(horizontal=20, vertical=24),
        scrollable=True,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
