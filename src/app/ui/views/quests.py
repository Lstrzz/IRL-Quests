"""Экран квестов: фильтры и список задач."""

from __future__ import annotations

import flet as ft

from ...models import DIFFICULTIES, coins_for_xp
from .. import theme as t
from ..components import empty_state, quest_card


class QuestsView:
    def __init__(self, app) -> None:
        self.app = app

    def build(self) -> ft.Control:
        state = self.app.state
        current = self.app.quest_filter

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Квесты", size=24, weight=ft.FontWeight.BOLD, color=t.TEXT),
                        ft.Text(
                            "Каждое выполненное дело — опыт и монеты",
                            size=12,
                            color=t.MUTED,
                        ),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                t.round_add(self.app.open_quest_dialog, "Новый квест"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        filters = ft.SegmentedButton(
            segments=[
                ft.Segment(value="available", label="Доступные"),
                ft.Segment(value="all", label="Все"),
                ft.Segment(value="done", label="Выполнено"),
            ],
            selected=[current],
            show_selected_icon=False,
            style=ft.ButtonStyle(
                color=t.MUTED,
                bgcolor=t.SURFACE,
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                text_style=ft.TextStyle(size=12, weight=ft.FontWeight.W_600),
            ),
            on_change=self._on_filter_change,
        )

        quests = list(state.quests)
        if current == "available":
            shown = [q for q in quests if q.is_available_today()]
        elif current == "done":
            shown = [q for q in quests if not q.is_available_today()]
        else:
            shown = quests

        shown.sort(key=lambda q: (not q.is_available_today(), q.repeat != "daily"))

        controls: list[ft.Control] = [header, filters]
        if shown:
            for quest in shown:
                controls.append(
                    quest_card(
                        quest,
                        on_complete=lambda q=quest: self.app.complete_quest(q.id),
                        on_actions=lambda q=quest: self.app.quest_actions(q),
                    )
                )
        else:
            if current == "done":
                controls.append(
                    empty_state(
                        "Пока пусто",
                        "Выполненные квесты появятся здесь.",
                        icon_data=ft.Icons.HISTORY_ROUNDED,
                    )
                )
            elif current == "available":
                controls.append(
                    empty_state(
                        "Всё выполнено!",
                        "На сегодня доступных квестов не осталось. Можно добавить новый.",
                        icon_data=ft.Icons.CELEBRATION_ROUNDED,
                        action="Новый квест",
                        on_action=self.app.open_quest_dialog,
                    )
                )
            else:
                controls.append(
                    empty_state(
                        "Квестов нет",
                        "Создай первую задачу и начни прокачку героя.",
                        icon_data=ft.Icons.FLAG_ROUNDED,
                        action="Создать квест",
                        on_action=self.app.open_quest_dialog,
                    )
                )

        controls.append(self._legend())
        controls.append(ft.Container(height=8))

        return ft.Column(
            controls,
            spacing=12,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _legend(self) -> ft.Control:
        items = [
            ft.Row(
                [
                    t.pill(name, color=t.DIFFICULTY_COLORS.get(key, t.MUTED)),
                    ft.Text(
                        f"{xp} XP · {coins_for_xp(xp)} монет",
                        size=11,
                        color=t.DIM,
                    ),
                ],
                spacing=6,
            )
            for key, (name, xp) in DIFFICULTIES.items()
        ]
        return ft.Column(
            [
                ft.Text("Сложность", size=11, color=t.DIM),
                ft.Row(items, spacing=14, wrap=True, run_spacing=8),
                ft.Text(
                    "Ежедневные квесты сбрасываются в полночь, еженедельные — в понедельник. "
                    "Удерживайте карточку, чтобы удалить квест.",
                    size=10,
                    color=t.DIM,
                ),
            ],
            spacing=8,
        )

    def _on_filter_change(self, e: ft.Event) -> None:
        selected = e.control.selected
        if selected:
            self.app.set_quest_filter(selected[0])
