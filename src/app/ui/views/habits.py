"""Экран привычек: серии, отметки и рекорды."""

from __future__ import annotations

import flet as ft

from ... import engine
from ...models import HABIT_DAY_EFFECT, HABIT_DIFFICULTIES
from .. import theme as t
from ..components import empty_state, habit_card


class HabitsView:
    def __init__(self, app) -> None:
        self.app = app

    def build(self) -> ft.Control:
        state = self.app.state
        habits = state.habits
        positives = [h for h in habits if not h.is_negative]
        checked_today = sum(1 for h in positives if h.done_today())
        multiplier = engine.day_multiplier(state)
        total_streak = engine.total_streak(state)
        best = max((h.best_streak for h in habits), default=0)

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Привычки", size=24, weight=ft.FontWeight.BOLD, color=t.TEXT),
                        ft.Text("Маленькие действия каждый день", size=12, color=t.MUTED),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                t.round_add(self.app.open_habit_dialog, "Новая привычка"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        summary = t.panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        "СЕРИЯ",
                                        size=10,
                                        color=ft.Colors.with_opacity(0.7, t.TEXT),
                                    ),
                                    ft.Row(
                                        [
                                            ft.Icon(
                                                ft.Icons.LOCAL_FIRE_DEPARTMENT_ROUNDED,
                                                color=t.ORANGE,
                                                size=28,
                                            ),
                                            ft.Text(
                                                str(total_streak),
                                                size=32,
                                                weight=ft.FontWeight.BOLD,
                                                color=t.TEXT,
                                            ),
                                            ft.Text("дней", size=12, color=t.MUTED),
                                        ],
                                        spacing=6,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    ),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                            t.stat_tile(
                                str(best),
                                "лучшая серия",
                                icon_data=ft.Icons.EMOJI_EVENTS_ROUNDED,
                                color=t.GOLD,
                            ),
                            t.stat_tile(
                                f"{checked_today}/{len(positives)}",
                                "сегодня",
                                icon_data=ft.Icons.CHECK_CIRCLE_ROUNDED,
                                color=t.ACCENT,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    t.progress_bar(
                        checked_today / len(positives) if positives else 0,
                        color=t.ACCENT,
                    ),
                ],
                spacing=10,
                tight=True,
            ),
            gradient=ft.LinearGradient(
                colors=["#123044", "#0D1B2A"],
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
            ),
            border=False,
            padding=18,
            radius=22,
        )

        controls: list[ft.Control] = [header]
        if habits:
            controls.append(summary)
            groups = [
                (
                    "Позитивные",
                    [h for h in habits if not h.is_negative],
                    f"заработок дня {engine._percent(multiplier)}",
                ),
                (
                    "Негативные",
                    [h for h in habits if h.is_negative],
                    "штраф, если срыв отмечен",
                ),
            ]
            for title, group, note in groups:
                if not group:
                    continue
                controls.append(
                    t.section_header(title, subtitle=f"{len(group)} · {note}")
                )
                for habit in group:
                    controls.append(
                        habit_card(
                            habit,
                            on_check_in=lambda h=habit: self.app.check_in_habit(h.id),
                            on_actions=lambda h=habit: self.app.habit_actions(h),
                        )
                    )
            controls.append(self._effect_legend())
            controls.append(self._hint())
        else:
            controls.append(
                empty_state(
                    "Привычек пока нет",
                    "Добавь привычку, отмечай её каждый день и собирай серию.",
                    icon_data=ft.Icons.LOOP_ROUNDED,
                    action="Добавить привычку",
                    on_action=self.app.open_habit_dialog,
                )
            )

        controls.append(ft.Container(height=8))

        return ft.Column(
            controls,
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _effect_legend(self) -> ft.Control:
        rows = [
            ft.Row(
                [
                    t.pill(HABIT_DIFFICULTIES[key][0], color=t.DIFFICULTY_COLORS.get(key, t.MUTED)),
                    ft.Text(
                        f"+{round(value * 100)}% / −{round(value * 100)}%",
                        size=11,
                        color=t.DIM,
                    ),
                ],
                spacing=6,
            )
            for key, value in HABIT_DAY_EFFECT.items()
        ]
        return ft.Column(
            [
                ft.Text("Заработок дня от привычек", size=11, color=t.DIM),
                ft.Row(rows, spacing=14, wrap=True, run_spacing=8),
                ft.Text(
                    "Позитивная отметка даёт бонус, негативная (срыв) — штраф к заработку "
                    "квестов и привычек до конца дня. Сильнее всего влияет сложность привычки.",
                    size=10,
                    color=t.DIM,
                ),
            ],
            spacing=8,
        )

    def _hint(self) -> ft.Control:
        return t.panel(
            ft.Row(
                [
                    ft.Icon(ft.Icons.TIPS_AND_UPDATES_ROUNDED, color=t.CYAN, size=20),
                    ft.Text(
                        "Отмечай привычку каждый день, чтобы не потерять серию. "
                        "Чем длиннее серия и выше сложность, тем больше опыта. "
                        "Удерживайте карточку, чтобы изменить или удалить привычку.",
                        size=11,
                        color=t.MUTED,
                        expand=True,
                    ),
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            bgcolor=ft.Colors.with_opacity(0.06, t.CYAN),
            border=False,
            radius=16,
            padding=14,
        )
