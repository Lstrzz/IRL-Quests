"""Карточки и мелкие составные элементы интерфейса."""

from __future__ import annotations

from typing import Callable

import flet as ft

from ..models import ATTRIBUTES, DIFFICULTIES, REPEATS, Achievement, Habit, Quest, Reward
from ..engine import attribute_level, attribute_progress
from . import theme as t

#: Прозрачность рамки карточки и кнопки выполнения.
CARD_BORDER_ALPHA = 0.18
#: Прозрачность подложки значков и заполненной кнопки выполнения.
ICON_BG_ALPHA = 0.14
#: Прозрачность рамки значков.
ICON_BORDER_ALPHA = 0.35

def _flat(groups: dict[str, list[str]]) -> list[str]:
    return [name for icons in groups.values() for name in icons]


#: Значки квеста по категориям (по 4 в каждой — ряд помещается на телефоне).
QUEST_ICON_GROUPS: dict[str, list[str]] = {
    "Тело": ["fitness_center", "directions_run", "sports_martial_arts", "self_improvement"],
    "Здоровье": ["local_hospital", "restaurant", "bedtime", "medication"],
    "Учёба": ["menu_book", "school", "translate", "code"],
    "Работа": ["task_alt", "work", "construction", "computer"],
    "Дом": ["cleaning_services", "shopping_cart", "savings", "local_florist"],
    "Досуг": ["brush", "music_note", "pets", "record_voice_over"],
}

#: Значки привычки по категориям.
HABIT_ICON_GROUPS: dict[str, list[str]] = {
    "Вода и еда": ["water_drop", "local_drink", "restaurant", "spa"],
    "Сон": ["bedtime", "nightlight", "wb_sunny", "timer"],
    "Разум": ["edit_note", "psychology", "air", "favorite"],
    "Тело": ["directions_walk", "fitness_center", "monitor_heart", "mood"],
    "Фокус": ["phone_disabled", "repeat", "event_available", "self_improvement"],
    "Природа": ["eco", "pets", "local_florist", "groups"],
    "Вредные": ["smoking_rooms", "local_bar", "fastfood", "phone_android"],
}

#: Значки награды по категориям.
REWARD_ICON_GROUPS: dict[str, list[str]] = {
    "Отдых": ["tv", "sports_esports", "movie", "headphones"],
    "Вкусно": ["cake", "icecream", "local_cafe", "local_pizza"],
    "Покупки": ["shopping_bag", "card_giftcard", "redeem", "diamond"],
    "Праздник": ["celebration", "toys", "theater_comedy", "beach_access"],
    "Путешествия": ["flight", "bike_scooter", "pool", "castle"],
    "Награды": ["emoji_events", "workspace_premium", "favorite", "spa"],
}

QUEST_ICON_CHOICES = _flat(QUEST_ICON_GROUPS)
HABIT_ICON_CHOICES = _flat(HABIT_ICON_GROUPS)
REWARD_ICON_CHOICES = _flat(REWARD_ICON_GROUPS)


class IconPicker:
    """Выбор значка для телефона: категории чипами и один ряд крупных значков."""

    def __init__(
        self,
        groups: dict[str, list[str]],
        selected: str,
        color: str,
    ) -> None:
        self.color = color
        self.chosen = False
        self.groups = {name: list(icons) for name, icons in groups.items()}
        if not any(selected in icons for icons in self.groups.values()):
            self.groups["Прочее"] = [selected]
        self.value = selected
        self.group = self._group_of(selected)

        self.chips: dict[str, ft.Container] = {
            name: ft.Container(
                content=ft.Text(name, size=12, weight=ft.FontWeight.W_600),
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                border_radius=12,
                ink=True,
                on_click=lambda e, n=name: self.open_group(n),
            )
            for name in self.groups
        }
        self.tiles: dict[str, ft.Container] = {
            name: ft.Container(
                content=ft.Icon(t.icon(name), size=26),
                width=56,
                height=56,
                border_radius=16,
                alignment=ft.Alignment.CENTER,
                ink=True,
                on_click=lambda e, n=name: self.select(n),
            )
            for icons in self.groups.values()
            for name in icons
        }
        self.preview = ft.Container(
            content=ft.Icon(t.icon(selected), size=28),
            width=56,
            height=56,
            border_radius=16,
            alignment=ft.Alignment.CENTER,
        )
        self._chip_row = ft.Row(
            [self.chips[name] for name in self.groups],
            spacing=8,
            run_spacing=8,
            wrap=True,
        )
        self._tile_row = ft.Row(self._group_tiles(), spacing=12, run_spacing=8, wrap=True)
        self._restyle()
        self.control = ft.Column(
            [
                ft.Row(
                    [
                        self.preview,
                        ft.Text("Значок", size=13, color=t.MUTED),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._chip_row,
                self._tile_row,
            ],
            spacing=10,
            tight=True,
        )

    def _group_of(self, name: str) -> str:
        return next(group for group, icons in self.groups.items() if name in icons)

    def _group_tiles(self) -> list[ft.Control]:
        return [self.tiles[name] for name in self.groups[self.group]]

    def select(self, name: str, *, manual: bool = True) -> None:
        self.value = name
        self.chosen = self.chosen or manual
        self.group = self._group_of(name)
        self._tile_row.controls = self._group_tiles()
        self._restyle()
        self._update()

    def open_group(self, name: str) -> None:
        self.group = name
        self._tile_row.controls = self._group_tiles()
        self._restyle()
        self._update()

    def recolor(self, color: str) -> None:
        self.color = color
        self._restyle()
        self._update()

    def _restyle(self) -> None:
        for name, tile in self.tiles.items():
            on = name == self.value
            tile.bgcolor = ft.Colors.with_opacity(ICON_BG_ALPHA, self.color) if on else None
            tile.border = ft.Border.all(
                2 if on else 1,
                self.color if on else ft.Colors.with_opacity(CARD_BORDER_ALPHA, self.color),
            )
            tile.content.color = self.color if on else t.MUTED
        for name, chip in self.chips.items():
            on = name == self.group
            chip.bgcolor = ft.Colors.with_opacity(ICON_BG_ALPHA, self.color) if on else t.SURFACE_2
            chip.content.color = self.color if on else t.MUTED
        self.preview.bgcolor = ft.Colors.with_opacity(ICON_BG_ALPHA, self.color)
        self.preview.border = ft.Border.all(2, self.color)
        self.preview.content.icon = t.icon(self.value)
        self.preview.content.color = self.color

    def _update(self) -> None:
        self.preview.update()
        self._chip_row.update()
        self._tile_row.update()


def _check_button(on_click: Callable, color: str) -> ft.Container:
    """Пустая круглая кнопка выполнения: галочка появится после нажатия."""
    return ft.Container(
        width=44,
        height=44,
        border=ft.Border.all(
            1.5, ft.Colors.with_opacity(CARD_BORDER_ALPHA, color)
        ),
        border_radius=22,
        alignment=ft.Alignment.CENTER,
        tooltip="Выполнить",
        ink=True,
        on_click=lambda e: on_click(),
    )


def _done_mark() -> ft.Container:
    """Отмеченная кнопка: зелёная заливка и зелёная галочка успеха."""
    return ft.Container(
        content=ft.Icon(ft.Icons.CHECK_ROUNDED, color=t.ACCENT, size=22),
        width=44,
        height=44,
        bgcolor=ft.Colors.with_opacity(ICON_BG_ALPHA, t.ACCENT),
        border=ft.Border.all(
            1.5, ft.Colors.with_opacity(CARD_BORDER_ALPHA, t.ACCENT)
        ),
        border_radius=22,
        alignment=ft.Alignment.CENTER,
        tooltip="Выполнено",
    )


def quest_card(
    quest: Quest,
    *,
    on_complete: Callable,
    on_actions: Callable,
    compact: bool = False,
) -> ft.Control:
    done = not quest.is_available_today()
    color = t.attr_color(quest.attribute)

    title = ft.Text(
        quest.title,
        size=15 if not compact else 14,
        weight=ft.FontWeight.W_600,
        color=t.MUTED if done else t.TEXT,
        max_lines=2,
        overflow=ft.TextOverflow.ELLIPSIS,
        style=ft.TextStyle(
            decoration=ft.TextDecoration.LINE_THROUGH if done else ft.TextDecoration.NONE
        ),
    )

    meta: list[ft.Control] = [
        t.pill(
            DIFFICULTIES.get(quest.difficulty, DIFFICULTIES["normal"])[0],
            color=t.DIFFICULTY_COLORS.get(quest.difficulty, t.MUTED),
        ),
    ]
    if quest.repeat != "daily":
        meta.append(t.pill(REPEATS.get(quest.repeat, quest.repeat), color=t.MUTED))

    details: list[ft.Control] = [title]
    if quest.description and not compact:
        details.append(
            ft.Text(
                quest.description,
                size=12,
                color=t.DIM,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )
    details.append(ft.Row(meta, spacing=6, wrap=True, run_spacing=6))

    trailing = (
        _done_mark() if done else _check_button(on_complete, color)
    )

    leading = ft.Container(
        content=ft.Icon(t.icon(quest.icon), color=color, size=21),
        width=42,
        height=42,
        bgcolor=ft.Colors.with_opacity(ICON_BG_ALPHA, color),
        border=ft.Border.all(
            1, ft.Colors.with_opacity(ICON_BORDER_ALPHA, color)
        ),
        border_radius=13,
        alignment=ft.Alignment.CENTER,
    )

    card = t.panel(
        ft.Row(
            [
                leading,
                ft.Column(details, spacing=6, expand=True, tight=True),
                trailing,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
        bgcolor=t.SURFACE_2 if done else t.SURFACE,
        border_color=ft.Colors.with_opacity(CARD_BORDER_ALPHA, color),
        radius=18,
    )
    return ft.GestureDetector(
        content=card,
        on_long_press=lambda e: on_actions(),
        on_secondary_tap=lambda e: on_actions(),
    )


def _harm_button(on_click: Callable, done: bool) -> ft.Container:
    """Кнопка срыва: предупреждающий значок вместо галочки."""
    return ft.Container(
        content=(
            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=t.DANGER, size=22) if done else None
        ),
        width=44,
        height=44,
        bgcolor=ft.Colors.with_opacity(ICON_BG_ALPHA, t.DANGER) if done else None,
        border=ft.Border.all(1.5, ft.Colors.with_opacity(CARD_BORDER_ALPHA, t.DANGER)),
        border_radius=22,
        alignment=ft.Alignment.CENTER,
        tooltip="Срыв отмечен" if done else "Отметить срыв",
        ink=not done,
        on_click=None if done else (lambda e: on_click()),
    )


def _harm_habit_card(
    habit: Habit,
    *,
    on_check_in: Callable,
    on_actions: Callable,
) -> ft.Control:
    done = habit.done_today()
    color = t.attr_color(habit.attribute)
    card = t.panel(
        ft.Row(
            [
                ft.Container(
                    content=ft.Icon(t.icon(habit.icon), color=color, size=21),
                    width=42,
                    height=42,
                    bgcolor=ft.Colors.with_opacity(ICON_BG_ALPHA, color),
                    border=ft.Border.all(1, ft.Colors.with_opacity(ICON_BORDER_ALPHA, color)),
                    border_radius=13,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(
                            habit.title,
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=t.MUTED if done else t.TEXT,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(
                            [
                                t.pill(
                                    habit.difficulty_name,
                                    color=t.DIFFICULTY_COLORS.get(habit.difficulty, t.MUTED),
                                    size=10,
                                ),
                            ],
                            spacing=6,
                            run_spacing=4,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                    tight=True,
                ),
                _harm_button(on_check_in, done),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
        bgcolor=t.SURFACE_2 if done else t.SURFACE,
        border_color=ft.Colors.with_opacity(CARD_BORDER_ALPHA, color),
        radius=18,
    )
    return ft.GestureDetector(
        content=card,
        on_long_press=lambda e: on_actions(),
        on_secondary_tap=lambda e: on_actions(),
    )


def habit_card(
    habit: Habit,
    *,
    on_check_in: Callable,
    on_actions: Callable,
) -> ft.Control:
    if habit.is_negative:
        return _harm_habit_card(habit, on_check_in=on_check_in, on_actions=on_actions)
    done = habit.done_today()
    broken = habit.is_broken()
    color = t.attr_color(habit.attribute)
    difficulty_color = t.DIFFICULTY_COLORS.get(habit.difficulty, t.MUTED)

    streak_color = t.ORANGE if habit.streak > 0 else t.DIM
    subtitle = f"Рекорд: {habit.best_streak} дн."
    if broken:
        subtitle = f"Серия прервана · рекорд {habit.best_streak}"
    elif habit.streak == 0:
        subtitle = "Начни серию сегодня"

    trailing = _done_mark() if done else _check_button(on_check_in, color)

    card = t.panel(
        ft.Row(
            [
                ft.Container(
                    content=ft.Icon(t.icon(habit.icon), color=color, size=21),
                    width=42,
                    height=42,
                    bgcolor=ft.Colors.with_opacity(ICON_BG_ALPHA, color),
                    border=ft.Border.all(
                        1, ft.Colors.with_opacity(ICON_BORDER_ALPHA, color)
                    ),
                    border_radius=13,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(
                            habit.title,
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=t.MUTED if done else t.TEXT,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED,
                                    size=15,
                                    color=streak_color,
                                ),
                                ft.Text(
                                    f"{habit.streak} дн.",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=streak_color,
                                ),
                                t.pill(
                                    habit.difficulty_name,
                                    color=difficulty_color,
                                    size=10,
                                ),
                                ft.Text(f"· {subtitle}", size=12, color=t.DIM),
                            ],
                            spacing=6,
                            run_spacing=4,
                            wrap=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                    tight=True,
                ),
                trailing,
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
        bgcolor=t.SURFACE_2 if done else t.SURFACE,
        border_color=ft.Colors.with_opacity(CARD_BORDER_ALPHA, color),
        radius=18,
    )
    return ft.GestureDetector(
        content=card,
        on_long_press=lambda e: on_actions(),
        on_secondary_tap=lambda e: on_actions(),
    )


def reward_card(
    reward: Reward,
    *,
    coins: int,
    on_buy: Callable,
    on_actions: Callable,
) -> ft.Control:
    affordable = coins >= reward.cost
    card = t.panel(
        ft.Row(
            [
                ft.Container(
                    content=ft.Icon(t.icon(reward.icon), color=t.GOLD, size=22),
                    width=46,
                    height=46,
                    bgcolor=ft.Colors.with_opacity(0.12, t.GOLD),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.35, t.GOLD)),
                    border_radius=14,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(
                            reward.title,
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=t.TEXT,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            f"Куплено раз: {reward.purchases}" if reward.purchases else "Ещё не открыто",
                            size=11,
                            color=t.DIM,
                        ),
                    ],
                    spacing=3,
                    expand=True,
                    tight=True,
                ),
                ft.Button(
                    content=str(reward.cost),
                    icon=ft.Icons.MONETIZATION_ON_ROUNDED,
                    icon_color=t.BG if affordable else t.DIM,
                    color=t.BG if affordable else t.DIM,
                    bgcolor=t.GOLD if affordable else t.SURFACE_2,
                    disabled=not affordable,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding.symmetric(
                            horizontal=12, vertical=10
                        ),
                        text_style=ft.TextStyle(
                            size=13, weight=ft.FontWeight.BOLD
                        ),
                    ),
                    on_click=lambda e: on_buy(),
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
        radius=18,
    )
    return ft.GestureDetector(
        content=card,
        on_long_press=lambda e: on_actions(),
        on_secondary_tap=lambda e: on_actions(),
    )


class QuantityStepper:
    """Выбор количества кнопками −/+ с крупными касаниями для телефона."""

    def __init__(
        self,
        *,
        maximum: int,
        minimum: int = 1,
        color: str = t.GOLD,
        on_change: Callable[[int], None] | None = None,
    ) -> None:
        self.value = minimum
        self.minimum = minimum
        self.maximum = max(minimum, maximum)
        self.on_change = on_change
        self._label = ft.Text(
            str(self.value),
            size=22,
            weight=ft.FontWeight.BOLD,
            color=t.TEXT,
            width=64,
            text_align=ft.TextAlign.CENTER,
        )
        button_style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            padding=0,
            bgcolor={
                ft.ControlState.DEFAULT: t.SURFACE_2,
                ft.ControlState.DISABLED: t.SURFACE,
            },
        )
        self._minus = ft.IconButton(
            icon=ft.Icons.REMOVE_ROUNDED,
            icon_color=color,
            icon_size=24,
            width=52,
            height=52,
            style=button_style,
            on_click=lambda e: self._step(-1),
        )
        self._plus = ft.IconButton(
            icon=ft.Icons.ADD_ROUNDED,
            icon_color=color,
            icon_size=24,
            width=52,
            height=52,
            style=button_style,
            on_click=lambda e: self._step(1),
        )
        self._sync()
        self.control = ft.Row(
            [self._minus, self._label, self._plus],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )

    def _sync(self) -> None:
        self._minus.disabled = self.value <= self.minimum
        self._plus.disabled = self.value >= self.maximum

    def _step(self, delta: int) -> None:
        new = min(max(self.value + delta, self.minimum), self.maximum)
        if new == self.value:
            return
        self.value = new
        self._label.value = str(new)
        self._sync()
        self.control.update()
        if self.on_change:
            self.on_change(new)


def inventory_card(reward: Reward, *, on_open: Callable) -> ft.Control:
    return t.panel(
        ft.Row(
            [
                ft.Container(
                    content=ft.Icon(t.icon(reward.icon), color=t.GOLD, size=22),
                    width=46,
                    height=46,
                    bgcolor=ft.Colors.with_opacity(0.12, t.GOLD),
                    border=ft.Border.all(1, ft.Colors.with_opacity(0.35, t.GOLD)),
                    border_radius=14,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Text(
                            reward.title,
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=t.TEXT,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        t.pill(f"×{reward.owned}", color=t.GOLD, size=12),
                    ],
                    spacing=6,
                    expand=True,
                    tight=True,
                ),
                ft.Button(
                    content="Использовать",
                    bgcolor=t.GOLD,
                    color=t.BG,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                        text_style=ft.TextStyle(size=13, weight=ft.FontWeight.BOLD),
                    ),
                    on_click=lambda e: on_open(),
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
        radius=18,
    )


def attribute_card(code: str, value: int) -> ft.Control:
    name = ATTRIBUTES[code][0]
    color = t.attr_color(code)
    level = attribute_level(value)
    return t.panel(
        ft.Row(
            [
                ft.Container(
                    content=ft.Icon(t.attr_icon(code), color=color, size=20),
                    width=40,
                    height=40,
                    bgcolor=ft.Colors.with_opacity(0.14, color),
                    border=ft.Border.all(
                        1, ft.Colors.with_opacity(0.35, color)
                    ),
                    border_radius=12,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(name, size=14, weight=ft.FontWeight.W_600, color=t.TEXT),
                                ft.Container(expand=True),
                                ft.Text(f"{value}", size=13, color=color, weight=ft.FontWeight.BOLD),
                            ]
                        ),
                        t.progress_bar(attribute_progress(value), color=color, height=6),
                        ft.Text(f"Ранг {level}", size=10, color=t.DIM),
                    ],
                    spacing=5,
                    expand=True,
                    tight=True,
                ),
            ],
            spacing=12,
        ),
        padding=12,
        radius=16,
    )


def achievement_tile(ach: Achievement) -> ft.Control:
    unlocked = bool(ach.unlocked_at)
    color = t.GOLD if unlocked else t.DIM
    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(
                        t.icon(ach.icon),
                        color=color,
                        size=24,
                    ),
                    width=48,
                    height=48,
                    bgcolor=ft.Colors.with_opacity(0.12 if unlocked else 0.05, color),
                    border_radius=14,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text(
                    ach.title,
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=t.TEXT if unlocked else t.MUTED,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(
                    ach.description,
                    size=10,
                    color=t.DIM if unlocked else t.DIM,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
        bgcolor=t.SURFACE,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.4, color) if unlocked else t.BORDER),
        border_radius=16,
        col={"xs": 6, "sm": 4, "md": 3},
    )


def empty_state(
    title: str,
    text: str,
    *,
    icon_data: ft.IconData = ft.Icons.AUTO_AWESOME_ROUNDED,
    action: str | None = None,
    on_action: Callable | None = None,
) -> ft.Container:
    controls: list[ft.Control] = [
        ft.Icon(icon_data, size=34, color=t.DIM),
        ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=t.TEXT),
        ft.Text(text, size=12, color=t.MUTED, text_align=ft.TextAlign.CENTER),
    ]
    if action and on_action:
        controls.append(t.ghost_button(action, on_action, color=t.ACCENT))
    return t.panel(
        ft.Column(
            controls,
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=24,
        border=False,
        radius=18,
    )
