"""Экран героя: характеристики, статистика, достижения, хроника."""

from __future__ import annotations

import flet as ft

from ... import engine
from ...models import ATTRIBUTES, level_title
from .. import theme as t
from ..components import achievement_tile, attribute_card

LOG_ICONS = {
    "quest": ft.Icons.TASK_ALT_ROUNDED,
    "habit": ft.Icons.LOOP_ROUNDED,
    "reward": ft.Icons.SHOPPING_BAG_ROUNDED,
    "achievement": ft.Icons.EMOJI_EVENTS_ROUNDED,
    "start": ft.Icons.ROCKET_LAUNCH_ROUNDED,
    "info": ft.Icons.INFO_OUTLINE_ROUNDED,
}


class HeroView:
    def __init__(self, app) -> None:
        self.app = app

    def build(self) -> ft.Control:
        state = self.app.state
        player = state.player
        unlocked = [a for a in state.achievements if a.unlocked_at]

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Герой", size=24, weight=ft.FontWeight.BOLD, color=t.TEXT),
                        ft.Text(
                            f"{level_title(player.level)} · уровень {player.level}",
                            size=12,
                            color=t.MUTED,
                        ),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                ft.IconButton(
                    icon=ft.Icons.EDIT_ROUNDED,
                    icon_color=t.MUTED,
                    tooltip="Настройки",
                    on_click=lambda e: self.app.open_settings(),
                ),
            ]
        )

        profile = t.panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.PERSON_ROUNDED,
                                    color=t.BG,
                                    size=30,
                                ),
                                width=58,
                                height=58,
                                gradient=ft.LinearGradient(
                                    colors=[t.ACCENT, t.CYAN],
                                    begin=ft.Alignment.TOP_LEFT,
                                    end=ft.Alignment.BOTTOM_RIGHT,
                                ),
                                border_radius=18,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        player.name,
                                        size=19,
                                        weight=ft.FontWeight.BOLD,
                                        color=t.TEXT,
                                    ),
                                    ft.Text(
                                        f"{player.xp} XP · {player.coins} монет",
                                        size=12,
                                        color=t.MUTED,
                                    ),
                                ],
                                spacing=2,
                                tight=True,
                                expand=True,
                            ),
                            t.pill(
                                f"LVL {player.level}",
                                color=t.GOLD,
                                size=11,
                            ),
                        ],
                        spacing=12,
                    ),
                    t.progress_bar(engine.xp_progress(state), color=t.ACCENT, height=8),
                    ft.Row(
                        [
                            ft.Text(
                                f"До уровня {player.level + 1}",
                                size=11,
                                color=t.MUTED,
                            ),
                            ft.Container(expand=True),
                            ft.Text(
                                f"{player.xp_in_level}/{player.xp_to_next_level} XP",
                                size=11,
                                color=t.TEXT,
                                weight=ft.FontWeight.W_600,
                            ),
                        ]
                    ),
                ],
                spacing=12,
                tight=True,
            ),
            gradient=ft.LinearGradient(
                colors=[t.SURFACE_2, t.SURFACE],
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
            ),
            padding=18,
            radius=22,
        )

        attr_cards: list[ft.Control] = []
        for code in ATTRIBUTES:
            card = attribute_card(code, state.attributes.get(code, 0))
            card.col = {"xs": 6}
            attr_cards.append(card)

        attributes_section = ft.Column(
            [
                t.section_header(
                    "Характеристики",
                    subtitle="Растут от квестов и привычек",
                ),
                ft.ResponsiveRow(attr_cards, spacing=10, run_spacing=10),
            ],
            spacing=10,
        )

        stats_section = ft.Column(
            [
                t.section_header("Статистика"),
                ft.ResponsiveRow(
                    [
                        self._stat(
                            ft.Icons.TASK_ALT_ROUNDED,
                            str(state.stats.quests_done),
                            "квестов",
                            t.ACCENT,
                        ),
                        self._stat(
                            ft.Icons.LOOP_ROUNDED,
                            str(state.stats.habits_done),
                            "отметок",
                            t.CYAN,
                        ),
                        self._stat(
                            ft.Icons.BOLT_ROUNDED,
                            str(state.stats.xp_earned),
                            "XP заработано",
                            t.GOLD,
                        ),
                        self._stat(
                            ft.Icons.SHOPPING_BAG_ROUNDED,
                            str(state.stats.rewards_bought),
                            "наград",
                            t.PINK,
                        ),
                    ],
                    spacing=10,
                    run_spacing=10,
                ),
            ],
            spacing=10,
        )

        achievements_section = ft.Column(
            [
                t.section_header(
                    "Достижения",
                    subtitle=f"Открыто {len(unlocked)} из {len(state.achievements)}",
                    action="Отчёт",
                    on_action=self.app.open_report_dialog,
                    action_icon=ft.Icons.SHARE_ROUNDED,
                ),
                ft.ResponsiveRow(
                    [achievement_tile(a) for a in state.achievements],
                    spacing=10,
                    run_spacing=10,
                    columns=12,
                ),
            ],
            spacing=10,
        )

        log_entries: list[ft.Control] = []
        for entry in state.log[:10]:
            kind = entry.get("kind", "info")
            at = entry.get("at", "")
            time_label = at[11:16] if len(at) >= 16 else ""
            log_entries.append(
                ft.Row(
                    [
                        ft.Icon(
                            LOG_ICONS.get(kind, ft.Icons.INFO_OUTLINE_ROUNDED),
                            size=15,
                            color=t.MUTED,
                        ),
                        ft.Text(
                            entry.get("text", ""),
                            size=12,
                            color=t.MUTED,
                            expand=True,
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(time_label, size=10, color=t.DIM),
                    ],
                    spacing=8,
                )
            )

        log_section = ft.Column(
            [
                t.section_header("Хроника"),
                t.panel(
                    ft.Column(
                        [
                            *log_entries,
                        ],
                        spacing=10,
                        tight=True,
                    )
                    if log_entries
                    else ft.Text("Событий пока нет", size=12, color=t.DIM),
                    padding=14,
                    radius=16,
                ),
            ],
            spacing=10,
        )

        return ft.Column(
            [
                header,
                profile,
                attributes_section,
                stats_section,
                achievements_section,
                log_section,
                ft.Container(height=8),
            ],
            spacing=16,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )

    def _stat(
        self,
        icon_data: ft.IconData,
        value: str,
        label: str,
        color: str,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon_data, size=18, color=color),
                    ft.Text(
                        value,
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=t.TEXT,
                    ),
                    ft.Text(
                        label,
                        size=10,
                        color=t.DIM,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=3,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=t.SURFACE,
            border=ft.Border.all(1, t.BORDER),
            border_radius=14,
            col={"xs": 6, "sm": 3},
        )
