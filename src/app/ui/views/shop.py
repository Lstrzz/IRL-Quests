"""Магазин наград: тратим заработанные монеты."""

from __future__ import annotations

import flet as ft

from ... import engine
from .. import theme as t
from ..components import empty_state, inventory_card, reward_card


class ShopView:
    def __init__(self, app) -> None:
        self.app = app

    def build(self) -> ft.Control:
        state = self.app.state
        coins = state.player.coins

        header = ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Награды", size=24, weight=ft.FontWeight.BOLD, color=t.TEXT),
                        ft.Text("Монеты заслуживают приятных покупок", size=12, color=t.MUTED),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                t.round_add(self.app.open_reward_dialog, "Новая награда"),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        balance = t.panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    ft.Icons.MONETIZATION_ON_ROUNDED,
                                    color=t.BG,
                                    size=30,
                                ),
                                width=54,
                                height=54,
                                gradient=ft.LinearGradient(
                                    colors=[t.GOLD, t.ORANGE],
                                    begin=ft.Alignment.TOP_LEFT,
                                    end=ft.Alignment.BOTTOM_RIGHT,
                                ),
                                border_radius=17,
                                alignment=ft.Alignment.CENTER,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Монеты",
                                        size=11,
                                        color=t.MUTED,
                                    ),
                                    ft.Text(
                                        str(coins),
                                        size=32,
                                        weight=ft.FontWeight.BOLD,
                                        color=t.TEXT,
                                    ),
                                ],
                                spacing=0,
                                tight=True,
                                expand=True,
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        "Заработано",
                                        size=10,
                                        color=t.DIM,
                                        text_align=ft.TextAlign.RIGHT,
                                    ),
                                    ft.Text(
                                        str(state.stats.coins_earned),
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                        color=t.GOLD,
                                        text_align=ft.TextAlign.RIGHT,
                                    ),
                                ],
                                spacing=1,
                                tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                spacing=10,
                tight=True,
            ),
            gradient=ft.LinearGradient(
                colors=["#2A2138", "#17131F"],
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
            ),
            padding=18,
            radius=22,
        )

        rewards = sorted(state.rewards, key=lambda r: r.cost)
        owned = engine.inventory(state)
        controls: list[ft.Control] = [header, balance]
        if owned:
            total = sum(r.owned for r in owned)
            controls.append(
                t.section_header(
                    "Инвентарь",
                    subtitle=f"{total} шт. · нажмите «Использовать» на карточке",
                )
            )
            for reward in owned:
                controls.append(
                    inventory_card(
                        reward,
                        on_open=lambda r=reward: self.app.open_inventory_dialog(r),
                    )
                )
        if rewards:
            controls.append(
                t.section_header(
                    "Магазин",
                    subtitle=f"{len(rewards)} наград(ы) в списке",
                )
            )
            for reward in rewards:
                controls.append(
                    reward_card(
                        reward,
                        coins=coins,
                        on_buy=lambda r=reward: self.app.open_buy_dialog(r),
                        on_actions=lambda r=reward: self.app.reward_actions(r),
                    )
                )
            controls.append(self._hint())
        else:
            controls.append(
                empty_state(
                    "Магазин пуст",
                    "Добавь награду, ради которой захочется выполнять квесты.",
                    icon_data=ft.Icons.REDEEM_ROUNDED,
                    action="Добавить награду",
                    on_action=self.app.open_reward_dialog,
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

    def _hint(self) -> ft.Control:
        return t.panel(
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.LIGHTBULB_ROUNDED, color=t.GOLD, size=18),
                            ft.Text(
                                "Как заработать монеты",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=t.TEXT,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        "Выполняй квесты и отмечай привычки. Чем выше сложность квеста "
                        "и длиннее серия привычки, тем больше монет. Покупай награду "
                        "сразу в нужном количестве: купленное попадает в инвентарь, "
                        "откуда её можно использовать. Удерживайте карточку награды, "
                        "чтобы изменить или удалить её.",
                        size=11,
                        color=t.MUTED,
                    ),
                ],
                spacing=8,
                tight=True,
            ),
            bgcolor=t.SURFACE,
            border=False,
            radius=16,
            padding=14,
        )
