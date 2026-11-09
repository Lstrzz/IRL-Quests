"""Отчёт героя: карточка с прогрессом, статистикой и достижениями для сохранения картинкой."""

from __future__ import annotations

from datetime import date

import flet as ft

from .. import engine
from ..models import ATTRIBUTES, GameState, level_title
from . import theme as t

REPORT_WIDTH = 340
_INNER = REPORT_WIDTH - 40
_TILE_WIDTH = (_INNER - 8) / 2


def _tile(value: str, label: str, color: str) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(label, size=10, color=t.MUTED, text_align=ft.TextAlign.CENTER),
            ],
            spacing=2,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        width=_TILE_WIDTH,
        padding=10,
        bgcolor=t.SURFACE_2,
        border_radius=14,
        alignment=ft.Alignment.CENTER,
    )


def build_hero_report(state: GameState) -> ft.Control:
    player = state.player
    stats = state.stats
    unlocked = [a for a in state.achievements if a.unlocked_at]
    progress = player.xp_in_level / max(1, player.xp_to_next_level)

    tiles = [
        _tile(str(stats.quests_done), "квестов выполнено", t.ACCENT),
        _tile(str(stats.habits_done), "привычек отмечено", t.CYAN),
        _tile(str(engine.total_streak(state)), "дней серий", t.ORANGE),
        _tile(str(stats.xp_earned), "XP заработано", t.PRIMARY),
        _tile(str(stats.rewards_used), "наград использовано", t.GOLD),
        _tile(str(stats.coins_earned), "монет заработано", t.GOLD),
    ]

    attributes = [
        ft.Row(
            [
                ft.Text(name, size=12, color=t.TEXT, expand=True),
                ft.Text(
                    f"ранг {engine.attribute_level(state.attributes.get(code, 0))}",
                    size=12,
                    weight=ft.FontWeight.W_600,
                    color=t.attr_color(code),
                ),
            ]
        )
        for code, (name, _) in ATTRIBUTES.items()
    ]

    badges = ft.Row(
        [t.pill(a.title, color=t.ACCENT, size=11) for a in unlocked],
        spacing=6,
        run_spacing=6,
        wrap=True,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Отчёт героя",
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color=t.TEXT,
                                ),
                                ft.Text(
                                    date.today().strftime("%d.%m.%Y"),
                                    size=11,
                                    color=t.MUTED,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                            expand=True,
                        ),
                        ft.Text("IRL Quests", size=11, color=t.DIM),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(player.name, size=16, weight=ft.FontWeight.W_600, color=t.TEXT),
                ft.Text(
                    f"Уровень {player.level} · {level_title(player.level)}",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=t.ACCENT,
                ),
                ft.ProgressBar(value=progress, color=t.ACCENT, bgcolor=t.SURFACE_2),
                ft.Text(
                    f"{player.xp_in_level} / {player.xp_to_next_level} XP до уровня {player.level + 1}",
                    size=11,
                    color=t.MUTED,
                ),
                ft.Row(tiles, spacing=8, run_spacing=8, wrap=True),
                ft.Column(attributes, spacing=6, tight=True),
                ft.Text(
                    f"Достижения: {len(unlocked)} из {len(state.achievements)}",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color=t.TEXT,
                ),
                badges,
            ],
            spacing=14,
            tight=True,
        ),
        width=REPORT_WIDTH,
        padding=20,
        bgcolor=t.BG,
    )
