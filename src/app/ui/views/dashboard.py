"""Главный экран: настроение, уровень, квесты дня."""

from __future__ import annotations

from datetime import date, datetime

import flet as ft

from ... import engine
from ...models import level_title
from .. import theme as t
from ..components import quest_card, empty_state


class DashboardView:
    def __init__(self, app) -> None:
        self.app = app

    def build(self) -> ft.Control:
        state = self.app.state
        player = state.player
        done, total = engine.today_progress(state)
        streak = engine.total_streak(state)
        unlocked = sum(1 for a in state.achievements if a.unlocked_at)
        quote = t.QUOTES[date.today().toordinal() % len(t.QUOTES)]

        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Доброе утро"
        elif 12 <= hour < 18:
            greeting = "Добрый день"
        elif 18 <= hour < 23:
            greeting = "Добрый вечер"
        else:
            greeting = "Доброй ночи"

        header = ft.Row(
            [
                ft.Container(
                    content=ft.Text(
                        str(player.level),
                        size=20,
                        weight=ft.FontWeight.BOLD,
                        color=t.BG,
                    ),
                    width=46,
                    height=46,
                    gradient=ft.LinearGradient(
                        colors=[t.ACCENT, t.CYAN],
                        begin=ft.Alignment.TOP_LEFT,
                        end=ft.Alignment.BOTTOM_RIGHT,
                    ),
                    border_radius=15,
                    alignment=ft.Alignment.CENTER,
                    tooltip="Уровень героя",
                ),
                ft.Column(
                    [
                        ft.Text(
                            f"{greeting}, {player.name}!",
                            size=17,
                            weight=ft.FontWeight.BOLD,
                            color=t.TEXT,
                        ),
                        ft.Text(engine.today_label(), size=12, color=t.MUTED),
                    ],
                    spacing=1,
                    tight=True,
                    expand=True,
                ),
                t.pill(
                    str(player.coins),
                    icon_data=ft.Icons.MONETIZATION_ON_ROUNDED,
                    color=t.GOLD,
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS_ROUNDED,
                    icon_color=t.MUTED,
                    icon_size=21,
                    tooltip="Настройки",
                    on_click=lambda e: self.app.open_settings(),
                ),
            ],
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        hero_card = t.panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        "УРОВЕНЬ",
                                        size=10,
                                        color=ft.Colors.with_opacity(0.7, t.TEXT),
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Text(
                                                str(player.level),
                                                size=38,
                                                weight=ft.FontWeight.BOLD,
                                                color=t.TEXT,
                                            ),
                                            ft.Column(
                                                [
                                                    ft.Text(
                                                        level_title(player.level),
                                                        size=13,
                                                        weight=ft.FontWeight.W_600,
                                                        color=t.ACCENT,
                                                    ),
                                                    ft.Text(
                                                        f"{player.xp} XP всего",
                                                        size=11,
                                                        color=ft.Colors.with_opacity(0.75, t.TEXT),
                                                    ),
                                                ],
                                                spacing=0,
                                                tight=True,
                                            ),
                                        ],
                                        spacing=10,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    *self._day_effect_badge(engine.day_multiplier(state)),
                                    self._hero_emblem(streak),
                                ],
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                tight=True,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        f"До уровня {player.level + 1}",
                                        size=11,
                                        color=ft.Colors.with_opacity(0.8, t.TEXT),
                                    ),
                                    ft.Container(expand=True),
                                    ft.Text(
                                        f"{player.xp_in_level} / {player.xp_to_next_level} XP",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=t.TEXT,
                                    ),
                                ]
                            ),
                            t.progress_bar(
                                engine.xp_progress(state),
                                color=t.ACCENT,
                                height=9,
                            ),
                        ],
                        spacing=6,
                        tight=True,
                    ),
                    ft.Container(
                        content=ft.Row(
                            [
                                t.stat_tile(
                                    str(streak),
                                    "серия дней",
                                    icon_data=ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED,
                                    color=t.ORANGE,
                                ),
                                ft.Container(width=1, height=30, bgcolor=ft.Colors.with_opacity(0.2, t.TEXT)),
                                t.stat_tile(
                                    f"{done}/{total}",
                                    "квестов сегодня",
                                    icon_data=ft.Icons.TASK_ALT_ROUNDED,
                                    color=t.ACCENT,
                                ),
                                ft.Container(width=1, height=30, bgcolor=ft.Colors.with_opacity(0.2, t.TEXT)),
                                t.stat_tile(
                                    str(unlocked),
                                    "достижений",
                                    icon_data=ft.Icons.EMOJI_EVENTS_ROUNDED,
                                    color=t.GOLD,
                                ),
                            ],
                            spacing=6,
                        ),
                        padding=ft.Padding.only(top=12),
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            gradient=ft.LinearGradient(
                colors=[t.PRIMARY, t.PRIMARY_DARK],
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
            ),
            border=False,
            padding=18,
            radius=24,
        )

        quests = engine.today_quests(state)
        quests.sort(key=lambda q: q.is_available_today() is False)

        quest_controls: list[ft.Control] = []
        for quest in quests:
            quest_controls.append(
                quest_card(
                    quest,
                    on_complete=lambda q=quest: self.app.complete_quest(q.id),
                    on_actions=lambda q=quest: self.app.quest_actions(q),
                    compact=True,
                )
            )
        if not quests:
            quest_controls.append(
                empty_state(
                    "Квестов пока нет",
                    "Добавь первую задачу и получи за неё опыт.",
                    icon_data=ft.Icons.FLAG_ROUNDED,
                    action="Создать квест",
                    on_action=self.app.open_quest_dialog,
                )
            )
        elif all(not q.is_available_today() for q in quests):
            quest_controls.insert(
                0,
                t.panel(
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.CELEBRATION_ROUNDED, color=t.GOLD, size=26),
                            ft.Text(
                                "План на сегодня выполнен. Отличная работа!",
                                size=13,
                                color=t.TEXT,
                                expand=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    bgcolor=ft.Colors.with_opacity(0.1, t.GOLD),
                    border=False,
                    radius=16,
                    padding=12,
                ),
            )

        today_section = ft.Column(
            [
                t.section_header(
                    "Квесты на сегодня",
                    subtitle=f"Выполнено {done} из {total}",
                    action="Все",
                    on_action=lambda: self.app.switch_tab(1),
                ),
                *quest_controls,
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        positive_chips = [
            self._mini_habit(h, h.done_today()) for h in state.habits if not h.is_negative
        ][:6]
        negative_chips = [
            self._mini_habit(h, h.done_today()) for h in state.habits if h.is_negative
        ][:6]
        habit_groups: list[ft.Control] = []
        if positive_chips:
            habit_groups.append(self._habit_group("Позитивные", positive_chips))
        if negative_chips:
            habit_groups.append(self._habit_group("Негативные", negative_chips))

        habits_section = ft.Column(
            [
                t.section_header(
                    "Привычки",
                    subtitle="Отметь то, что уже сделано",
                    action="Все",
                    on_action=lambda: self.app.switch_tab(2),
                ),
                *(
                    habit_groups
                    or [
                        empty_state(
                            "Пока ни одной привычки",
                            "Привычки дают опыт каждый день и растит серию.",
                            icon_data=ft.Icons.LOOP_ROUNDED,
                            action="Добавить привычку",
                            on_action=self.app.open_habit_dialog,
                        )
                    ]
                ),
            ],
            spacing=10,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

        next_achievement = next((a for a in state.achievements if not a.unlocked_at), None)
        achievement_block: ft.Control | None = None
        if next_achievement:
            achievement_block = t.panel(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.LOCK_OUTLINE_ROUNDED, color=t.GOLD, size=20),
                            width=40,
                            height=40,
                            bgcolor=ft.Colors.with_opacity(0.1, t.GOLD),
                            border_radius=12,
                            alignment=ft.Alignment.CENTER,
                        ),
                        ft.Column(
                            [
                                ft.Text("Следующая цель", size=10, color=t.DIM),
                                ft.Text(
                                    next_achievement.title,
                                    size=13,
                                    weight=ft.FontWeight.W_600,
                                    color=t.TEXT,
                                ),
                                ft.Text(
                                    next_achievement.description,
                                    size=11,
                                    color=t.MUTED,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=1,
                            tight=True,
                            expand=True,
                        ),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, color=t.DIM, size=20),
                    ],
                    spacing=10,
                ),
                padding=12,
                radius=16,
                on_click=lambda e: self.app.switch_tab(3),
                ink=True,
            )

        quote_block = t.panel(
            ft.Row(
                [
                    ft.Icon(ft.Icons.FORMAT_QUOTE_ROUNDED, color=t.MUTED, size=20),
                    ft.Text(
                        quote,
                        size=12,
                        color=t.MUTED,
                        italic=True,
                        expand=True,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            bgcolor=t.SURFACE,
            border=False,
            radius=16,
            padding=14,
        )

        controls: list[ft.Control] = [header, hero_card, today_section]
        if state.habits:
            controls.append(habits_section)
        if achievement_block is not None:
            controls.append(achievement_block)
        controls.append(quote_block)
        controls.append(ft.Container(height=8))

        return ft.Column(
            controls,
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _hero_emblem(self, streak: int) -> ft.Control:
        """Щит разгорается к 30 дням, затем месяц растёт огонёк и меняет цвет."""
        shield_alpha = engine.shield_opacity(streak)
        shield_progress = (shield_alpha - 0.25) / 0.75
        flame = engine.flame_progress(streak)
        flame_color = engine.flame_color(streak)

        shield = ft.Icon(
            ft.Icons.SHIELD_ROUNDED,
            size=54,
            color=ft.Colors.with_opacity(shield_alpha, t.TEXT),
            shadows=ft.BoxShadow(
                blur_radius=8 + 16 * shield_progress,
                color=ft.Colors.with_opacity(
                    0.10 + 0.25 * shield_progress, t.PRIMARY
                ),
            ),
            semantics_label=f"Щит героя: серия {streak} дней",
            tooltip=(
                f"Щит: {min(streak, engine.SHIELD_FULL_DAYS)}"
                f"/{engine.SHIELD_FULL_DAYS} дн. серии"
            ),
        )

        flame_icon = ft.Icon(
            ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED,
            size=10 + 20 * flame,
            color=ft.Colors.with_opacity(0.35 + 0.65 * flame, flame_color),
            shadows=[
                ft.BoxShadow(
                    spread_radius=1,
                    blur_radius=2,
                    color=ft.Colors.with_opacity(0.45, t.BG),
                ),
                ft.BoxShadow(
                    blur_radius=4 + 12 * flame,
                    color=ft.Colors.with_opacity(0.35 * flame, flame_color),
                ),
            ],
            semantics_label=f"Огонь серии: {streak} дней",
            tooltip=f"Огонь серии: {streak} дн.",
            visible=flame > 0,
        )

        return ft.Stack(
            width=60,
            height=60,
            alignment=ft.Alignment.CENTER,
            clip_behavior=ft.ClipBehavior.NONE,
            controls=[shield, flame_icon],
        )

    def _day_effect_badge(self, multiplier: float) -> list[ft.Control]:
        """Значок зелья с итоговой суммой эффектов дня: зелёный при плюсе, красный при минусе."""
        percent = round((multiplier - 1.0) * 100)
        if percent == 0:
            return []
        positive = percent > 0
        color = t.ACCENT if positive else t.DANGER
        text = f"{'+' if positive else '−'}{abs(percent)}%"
        return [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.SCIENCE_ROUNDED, color=color, size=16),
                        ft.Text(
                            text,
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color=color,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                padding=ft.Padding.symmetric(horizontal=8, vertical=5),
                bgcolor=ft.Colors.with_opacity(0.14, color),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.35, color)),
                border_radius=10,
                tooltip=f"Итог дня от привычек: {text} к заработку",
            )
        ]

    def _habit_group(self, title: str, chips: list[ft.Control]) -> ft.Control:
        # Сетка вместо горизонтальной прокрутки: иначе полоса прокрутки
        # перекрывает нижний край карточек привычек.
        return ft.Column(
            [
                ft.Text(title, size=12, weight=ft.FontWeight.W_600, color=t.MUTED),
                ft.ResponsiveRow(chips, spacing=8, run_spacing=8, columns=12),
            ],
            spacing=8,
        )

    def _mini_habit(self, habit, done: bool) -> ft.Control:
        color = t.attr_color(habit.attribute)
        if habit.is_negative:
            icon_data = ft.Icons.WARNING_AMBER_ROUNDED if done else t.icon(habit.icon)
            icon_color = t.DANGER if done else color
            status = "Срыв отмечен" if done else "Не отмечено"
            status_color = t.DANGER if done else t.DIM
        else:
            icon_data = ft.Icons.CHECK_CIRCLE_ROUNDED if done else t.icon(habit.icon)
            icon_color = t.ACCENT if done else color
            status = "Выполнено" if done else f"Серия: {habit.streak} дн."
            status_color = t.ACCENT if done else t.DIM
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon_data, size=18, color=icon_color),
                    ft.Column(
                        [
                            ft.Text(
                                habit.title,
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=t.MUTED if done else t.TEXT,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                status,
                                size=10,
                                color=status_color,
                            ),
                        ],
                        spacing=1,
                        tight=True,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            bgcolor=t.SURFACE,
            border=ft.Border.all(1, t.BORDER),
            border_radius=14,
            col={"xs": 6, "sm": 4, "md": 3, "lg": 2},
            on_click=lambda e: (
                None if done else self.app.check_in_habit(habit.id)
            ),
            ink=not done,
        )
