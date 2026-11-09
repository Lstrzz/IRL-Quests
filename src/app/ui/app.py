"""Корневой контроллер приложения: вкладки, диалоги, сохранение."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

import flet as ft

from .. import engine
from ..models import (
    ATTRIBUTES,
    DIFFICULTIES,
    HABIT_DIFFICULTIES,
    HABIT_KINDS,
    REPEATS,
    Habit,
    Quest,
    Reward,
)
from ..storage import (
    MAX_SAVE_SIZE,
    Storage,
    data_dir,
    save_bytes,
    state_from_bytes,
)
from . import theme as t
from .report import build_hero_report
from .components import (
    HABIT_ICON_GROUPS,
    QUEST_ICON_GROUPS,
    REWARD_ICON_GROUPS,
    IconPicker,
    QuantityStepper,
)
from .views.dashboard import DashboardView
from .views.habits import HabitsView
from .views.hero import HeroView
from .views.quests import QuestsView
from .views.shop import ShopView

QUEST_ICONS = {
    "strength": "fitness_center",
    "intellect": "menu_book",
    "will": "task_alt",
    "charisma": "record_voice_over",
}

HABIT_ICONS = {
    "strength": "water_drop",
    "intellect": "edit_note",
    "will": "self_improvement",
    "charisma": "groups",
}


class IRLApp:
    """Собирает состояние, вкладки и обработчики действий."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.storage = Storage()
        self.state = self.storage.load()
        self.tab = 0
        self.quest_filter = "available"
        self.file_picker = ft.FilePicker(on_result=self.import_save_result)

        self.body = ft.Container(expand=True, padding=ft.Padding.only(left=16, right=16, top=8))
        self.nav = ft.NavigationBar(
            selected_index=0,
            bgcolor=t.SURFACE,
            indicator_color=ft.Colors.with_opacity(0.18, t.PRIMARY),
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
            border=ft.Border.only(top=ft.BorderSide(1, t.BORDER)),
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.SPACE_DASHBOARD_OUTLINED,
                    selected_icon=ft.Icons.SPACE_DASHBOARD_ROUNDED,
                    label="Главная",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.CHECKLIST_OUTLINED,
                    selected_icon=ft.Icons.CHECKLIST_ROUNDED,
                    label="Квесты",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.LOOP_OUTLINED,
                    selected_icon=ft.Icons.LOOP_ROUNDED,
                    label="Привычки",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SHIELD_OUTLINED,
                    selected_icon=ft.Icons.SHIELD_ROUNDED,
                    label="Герой",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SHOPPING_BAG_OUTLINED,
                    selected_icon=ft.Icons.SHOPPING_BAG_ROUNDED,
                    label="Награды",
                ),
            ],
            on_change=self._on_tab_change,
        )

        self.views = [
            DashboardView(self),
            QuestsView(self),
            HabitsView(self),
            HeroView(self),
            ShopView(self),
        ]

    # ------------------------------------------------------------------
    # Запуск
    # ------------------------------------------------------------------

    def mount(self) -> None:
        page = self.page
        page.title = "IRL Quests"
        page.enable_screenshots = True
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = t.BG
        page.padding = 0
        page.theme = ft.Theme(
            color_scheme=ft.ColorScheme(
                primary=t.PRIMARY,
                on_primary=t.TEXT,
                secondary=t.ACCENT,
                on_secondary=t.BG,
                surface=t.SURFACE,
                on_surface=t.TEXT,
                error=t.DANGER,
                on_error=t.BG,
            ),
            scaffold_bgcolor=t.BG,
            use_material3=True,
            dialog_theme=t.dialog_theme(),
            dropdown_theme=t.dropdown_theme(),
            popup_menu_theme=t.popup_menu_theme(),
            snackbar_theme=t.snackbar_theme(),
        )
        page.navigation_bar = self.nav
        page.services.append(self.file_picker)
        page.add(ft.SafeArea(content=self.body, expand=True))
        self.refresh()

    def _on_tab_change(self, e: ft.Event) -> None:
        self.tab = e.control.selected_index
        self.refresh()

    def switch_tab(self, index: int) -> None:
        """Программно переключает вкладку (кнопки «Все», карточки-ссылки)."""
        index = max(0, min(index, len(self.views) - 1))
        self.tab = index
        self.nav.selected_index = index
        self.nav.update()
        self.refresh()

    def refresh(self) -> None:
        self.body.content = self.views[self.tab].build()
        self.body.update()

    def persist(self, *, refresh: bool = True) -> None:
        try:
            self.storage.save(self.state)
        except OSError as exc:
            self.show_snack(f"Не удалось сохранить: {exc}", "error")
        if refresh:
            self.refresh()

    # ------------------------------------------------------------------
    # Уведомления
    # ------------------------------------------------------------------

    def show_snack(self, text: str, kind: str = "info") -> None:
        colors = {
            "error": (t.DANGER, t.BG),
            "levelup": (t.GOLD, t.BG),
            "achievement": (t.PRIMARY, t.TEXT),
            "coins": (t.SURFACE_2, t.TEXT),
            "info": (t.SURFACE_2, t.TEXT),
        }
        bg, fg = colors.get(kind, (t.SURFACE_2, t.TEXT))
        icons = {
            "error": ft.Icons.ERROR_OUTLINE_ROUNDED,
            "levelup": ft.Icons.ARROW_UPWARD_ROUNDED,
            "achievement": ft.Icons.EMOJI_EVENTS_ROUNDED,
            "coins": ft.Icons.MONETIZATION_ON_ROUNDED,
        }
        controls: list[ft.Control] = []
        if kind in icons:
            controls.append(ft.Icon(icons[kind], color=fg, size=18))
        controls.append(ft.Text(text, size=13, color=fg, weight=ft.FontWeight.W_500))
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Row(controls, spacing=8, tight=True),
                bgcolor=bg,
                behavior=ft.SnackBarBehavior.FLOATING,
                margin=ft.Margin.only(left=16, right=16, bottom=12),
                duration=2600,
                shape=ft.RoundedRectangleBorder(radius=14),
            )
        )

    def notify(self, events: list[engine.Event]) -> None:
        if not events:
            return
        priority = {"error": 5, "levelup": 4, "achievement": 3, "coins": 2, "xp": 1, "info": 0}
        events = sorted(events, key=lambda e: priority.get(e.kind, 0), reverse=True)
        main = events[0]
        text = main.text
        if len(events) > 1:
            text += f"  ·  {events[1].text}"
        self.show_snack(text, main.kind)

    # ------------------------------------------------------------------
    # Действия
    # ------------------------------------------------------------------

    def complete_quest(self, quest_id: str) -> None:
        events = engine.complete_quest(self.state, quest_id)
        self.persist()
        self.notify(events)

    def check_in_habit(self, habit_id: str) -> None:
        events = engine.check_in_habit(self.state, habit_id)
        self.persist()
        self.notify(events)

    def open_buy_dialog(self, reward: Reward) -> None:
        coins = self.state.player.coins
        total = ft.Text(
            f"Итого: {reward.cost} монет · у вас {coins}",
            size=13,
            color=t.MUTED,
        )

        def on_quantity(quantity: int) -> None:
            total.value = (
                f"Итого: {quantity * reward.cost} монет · у вас {coins}"
            )
            total.update()

        stepper = QuantityStepper(
            maximum=min(99, max(1, coins // reward.cost)),
            on_change=on_quantity,
        )

        def buy() -> None:
            events = engine.buy_reward(self.state, reward.id, stepper.value)
            self.close_dialog()
            self.persist()
            self.notify(events)

        self.page.show_dialog(
            t.dialog_shell(
                "Покупка",
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(t.icon(reward.icon), color=t.GOLD, size=26),
                                ft.Column(
                                    [
                                        ft.Text(
                                            reward.title,
                                            size=15,
                                            weight=ft.FontWeight.W_600,
                                            color=t.TEXT,
                                        ),
                                        ft.Text(
                                            f"Цена: {reward.cost} монет",
                                            size=12,
                                            color=t.MUTED,
                                        ),
                                    ],
                                    spacing=2,
                                    tight=True,
                                ),
                            ],
                            spacing=12,
                        ),
                        stepper.control,
                        total,
                    ],
                    spacing=14,
                    tight=True,
                ),
                self._dialog_actions(buy, "Купить"),
                icon_data=ft.Icons.SHOPPING_BAG_ROUNDED,
                icon_color=t.GOLD,
            )
        )

    def open_report_dialog(self) -> None:
        shot = ft.Screenshot(content=build_hero_report(self.state))

        async def save() -> None:
            png = await shot.capture(pixel_ratio=2)
            folder = data_dir() / "reports"
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"hero_report_{date.today().isoformat()}.png"
            path.write_bytes(png)
            self.close_dialog()
            self.show_snack(f"Отчёт сохранён: {path}", "info")

        self.page.show_dialog(
            t.dialog_shell(
                "Отчёт героя",
                ft.Column([shot], scroll=ft.ScrollMode.AUTO, tight=True),
                [
                    t.ghost_button("Закрыть", self.close_dialog),
                    t.primary_button(
                        "Сохранить PNG",
                        lambda: self.page.run_task(save),
                        icon_data=ft.Icons.SAVE_ALT_ROUNDED,
                    ),
                ],
                icon_data=ft.Icons.SHARE_ROUNDED,
            )
        )

    def open_inventory_dialog(self, reward: Reward) -> None:
        def use() -> None:
            events = engine.use_reward(self.state, reward.id, stepper.value)
            self.close_dialog()
            self.persist()
            self.notify(events)

        stepper = QuantityStepper(maximum=reward.owned)
        self.page.show_dialog(
            t.dialog_shell(
                reward.title,
                ft.Column(
                    [
                        ft.Text(
                            f"В инвентаре: {reward.owned}",
                            size=13,
                            color=t.MUTED,
                        ),
                        stepper.control,
                    ],
                    spacing=14,
                    tight=True,
                ),
                self._dialog_actions(use, "Использовать"),
                icon_data=t.icon(reward.icon),
                icon_color=t.GOLD,
            )
        )

    def set_quest_filter(self, value: str) -> None:
        self.quest_filter = value
        self.refresh()

    # ------------------------------------------------------------------
    # Диалоги
    # ------------------------------------------------------------------

    def close_dialog(self) -> None:
        self.page.pop_dialog()

    def _dialog_actions(self, on_save, save_label: str = "Сохранить") -> list[ft.Control]:
        return [
            t.ghost_button("Отмена", self.close_dialog),
            t.primary_button(save_label, on_save),
        ]

    def _action_row(
        self,
        label: str,
        icon: ft.IconData,
        color: str,
        on_click: Callable,
    ) -> ft.Control:
        """Крупная строка действия внутри диалога карточки."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=color,
                    ),
                ],
                spacing=10,
                tight=True,
            ),
            padding=ft.Padding.symmetric(horizontal=14, vertical=13),
            bgcolor=ft.Colors.with_opacity(0.08, color),
            border=ft.Border.all(1, ft.Colors.with_opacity(0.25, color)),
            border_radius=12,
            ink=True,
            on_click=lambda e: on_click(),
        )

    def _open_actions(
        self,
        title: str,
        subject: str,
        actions: list[tuple[str, ft.IconData, str, Callable]],
        *,
        icon_data: ft.IconData,
        icon_color: str = t.PRIMARY,
    ) -> None:
        content: list[ft.Control] = [
            ft.Text(
                subject,
                size=13,
                color=t.MUTED,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        ]
        content.extend(
            self._action_row(label, icon, color, handler)
            for label, icon, color, handler in actions
        )
        self.page.show_dialog(
            t.dialog_shell(
                title,
                ft.Column(
                    content,
                    spacing=8,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                [t.ghost_button("Закрыть", self.close_dialog)],
                icon_data=icon_data,
                icon_color=icon_color,
            )
        )

    def open_quest_dialog(self, quest: Quest | None = None) -> None:
        editing = quest is not None
        title = t.text_field(
            "Название квеста",
            hint="Пробежка 3 км",
            value=quest.title if editing else "",
        )
        description = t.text_field(
            "Описание (необязательно)",
            multiline=True,
            value=quest.description if editing else "",
        )
        difficulty = t.dropdown(
            "Сложность",
            [(key, f"{name} · {xp} XP") for key, (name, xp) in DIFFICULTIES.items()],
            value=quest.difficulty if editing else "normal",
        )
        attribute = t.dropdown(
            "Характеристика",
            [(key, name) for key, (name, _) in ATTRIBUTES.items()],
            value=quest.attribute if editing else "will",
        )
        repeat = t.dropdown(
            "Повтор",
            list(REPEATS.items()),
            value=quest.repeat if editing else "daily",
        )
        start_attr = quest.attribute if editing else "will"
        picker = IconPicker(
            QUEST_ICON_GROUPS,
            quest.icon if editing else QUEST_ICONS["will"],
            t.attr_color(start_attr),
        )

        def on_attribute(e: ft.Event) -> None:
            code = attribute.value or "will"
            if not picker.chosen:
                picker.select(QUEST_ICONS.get(code, "flag"), manual=False)
            picker.recolor(t.attr_color(code))

        attribute.on_change = on_attribute

        def save() -> None:
            if not (title.value or "").strip():
                title.error = ft.Text("Придумай название", size=11, color=t.DANGER)
                title.update()
                return
            cleaned = title.value.strip()
            description_value = (description.value or "").strip()
            attr = attribute.value or "will"
            level = difficulty.value or "normal"
            repeat_value = repeat.value or "daily"
            if editing:
                events = engine.update_quest(
                    self.state,
                    quest.id,
                    title=cleaned,
                    description=description_value,
                    attribute=attr,
                    difficulty=level,
                    repeat=repeat_value,
                    icon=picker.value,
                )
            else:
                events = engine.add_quest(
                    self.state,
                    Quest(
                        title=cleaned,
                        description=description_value,
                        attribute=attr,
                        difficulty=level,
                        repeat=repeat_value,
                        icon=picker.value,
                    ),
                )
            self.close_dialog()
            self.persist()
            if events:
                self.notify(events)
            else:
                action = "изменён" if editing else "добавлен"
                self.show_snack(f"Квест «{cleaned}» {action}", "info")

        self.page.show_dialog(
            t.dialog_shell(
                "Изменить квест" if editing else "Новый квест",
                ft.Column(
                    [title, description, difficulty, attribute, repeat, picker.control],
                    spacing=12,
                    tight=True,
                ),
                self._dialog_actions(save, "Сохранить" if editing else "Добавить"),
                icon_data=ft.Icons.EDIT_ROUNDED if editing else ft.Icons.ADD_TASK_ROUNDED,
            )
        )

    def open_habit_dialog(self, habit: Habit | None = None) -> None:
        editing = habit is not None
        title = t.text_field(
            "Название привычки",
            hint="10 000 шагов",
            value=habit.title if editing else "",
        )
        difficulty = t.dropdown(
            "Сложность",
            [
                (key, f"{name} · {xp} XP")
                for key, (name, xp) in HABIT_DIFFICULTIES.items()
            ],
            value=habit.difficulty if editing else "normal",
        )
        attribute = t.dropdown(
            "Характеристика",
            [(key, name) for key, (name, _) in ATTRIBUTES.items()],
            value=habit.attribute if editing else "will",
        )
        kind = t.dropdown(
            "Тип",
            list(HABIT_KINDS.items()),
            value=habit.kind if editing else "positive",
        )
        start_attr = habit.attribute if editing else "will"
        picker = IconPicker(
            HABIT_ICON_GROUPS,
            habit.icon if editing else HABIT_ICONS.get(start_attr, "repeat"),
            t.attr_color(start_attr),
        )

        def on_attribute(e: ft.Event) -> None:
            code = attribute.value or "will"
            if not picker.chosen:
                picker.select(HABIT_ICONS.get(code, "repeat"), manual=False)
            picker.recolor(t.attr_color(code))

        attribute.on_change = on_attribute

        def save() -> None:
            cleaned = (title.value or "").strip()
            if not cleaned:
                title.error = ft.Text("Придумай название", size=11, color=t.DANGER)
                title.update()
                return
            attr = attribute.value or "will"
            icon = picker.value
            level = difficulty.value or "normal"
            habit_kind = kind.value or "positive"
            if editing:
                events = engine.update_habit(
                    self.state,
                    habit.id,
                    title=cleaned,
                    attribute=attr,
                    difficulty=level,
                    icon=icon,
                    kind=habit_kind,
                )
            else:
                events = engine.add_habit(
                    self.state,
                    Habit(
                        title=cleaned,
                        attribute=attr,
                        difficulty=level,
                        icon=icon,
                        kind=habit_kind,
                    ),
                )
            self.close_dialog()
            self.persist()
            if events:
                self.notify(events)
            else:
                action = "изменена" if editing else "добавлена"
                self.show_snack(f"Привычка «{cleaned}» {action}", "info")

        self.page.show_dialog(
            t.dialog_shell(
                "Изменить привычку" if editing else "Новая привычка",
                ft.Column(
                    [title, difficulty, kind, attribute, picker.control],
                    spacing=12,
                    tight=True,
                ),
                self._dialog_actions(
                    save, "Сохранить" if editing else "Добавить"
                ),
                icon_data=(
                    ft.Icons.EDIT_ROUNDED if editing else ft.Icons.LOOP_ROUNDED
                ),
            )
        )

    def open_reward_dialog(self, reward: Reward | None = None) -> None:
        editing = reward is not None
        title = t.text_field(
            "Название награды",
            hint="Поход в кино",
            value=reward.title if editing else "",
        )
        cost = t.text_field(
            "Стоимость в монетах",
            value=str(reward.cost) if editing else "100",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        picker = IconPicker(
            REWARD_ICON_GROUPS,
            reward.icon if editing else "redeem",
            t.GOLD,
        )

        def save() -> None:
            cleaned = (title.value or "").strip()
            if not cleaned:
                title.error = ft.Text("Придумай название", size=11, color=t.DANGER)
                title.update()
                return
            try:
                value = max(1, int(cost.value or "100"))
            except ValueError:
                value = 100

            if editing:
                engine.update_reward(
                    self.state,
                    reward.id,
                    title=cleaned,
                    cost=value,
                    icon=picker.value,
                )
                message = f"Награда «{cleaned}» обновлена"
            else:
                engine.add_reward(
                    self.state,
                    Reward(title=cleaned, cost=value, icon=picker.value),
                )
                message = f"Награда «{cleaned}» добавлена"

            self.close_dialog()
            self.persist()
            self.show_snack(message, "info")

        self.page.show_dialog(
            t.dialog_shell(
                "Изменить награду" if editing else "Новая награда",
                ft.Column([title, cost, picker.control], spacing=12, tight=True),
                self._dialog_actions(save, "Сохранить" if editing else "Добавить"),
                icon_data=ft.Icons.EDIT_ROUNDED if editing else ft.Icons.REDEEM_ROUNDED,
            )
        )

    def delete_reward(self, reward_id: str) -> None:
        reward = self.state.reward_by_id(reward_id)
        if not reward:
            return

        def action() -> None:
            engine.delete_reward(self.state, reward_id)
            self.persist()
            self.show_snack("Награда удалена", "info")

        bought = (
            f"Куплено раз: {reward.purchases}. "
            if reward.purchases
            else ""
        )
        self.confirm(
            "Удалить награду?",
            f"{bought}«{reward.title}» исчезнет из магазина.",
            action,
        )

    def confirm(
        self,
        title: str,
        text: str,
        action,
        *,
        danger: bool = True,
        ok_label: str | None = None,
    ) -> None:
        def run() -> None:
            self.close_dialog()
            action()

        self.page.show_dialog(
            t.dialog_shell(
                title,
                ft.Text(text, size=13, color=t.MUTED),
                [
                    t.ghost_button("Отмена", self.close_dialog),
                    t.primary_button(
                        ok_label or ("Удалить" if danger else "ОК"),
                        run,
                        color=t.DANGER if danger else t.ACCENT,
                    ),
                ],
                icon_data=(
                    ft.Icons.WARNING_AMBER_ROUNDED
                    if danger
                    else ft.Icons.INFO_OUTLINE_ROUNDED
                ),
                icon_color=t.DANGER if danger else t.ACCENT,
            )
        )

    def delete_quest(self, quest_id: str) -> None:
        quest = self.state.quest_by_id(quest_id)
        if not quest:
            return

        def action() -> None:
            engine.delete_quest(self.state, quest_id)
            self.persist()
            self.show_snack("Квест удалён", "info")

        self.confirm("Удалить квест?", f"«{quest.title}» исчезнет безвозвратно.", action)

    def delete_habit(self, habit_id: str) -> None:
        habit = self.state.habit_by_id(habit_id)
        if not habit:
            return

        def action() -> None:
            engine.delete_habit(self.state, habit_id)
            self.persist()
            self.show_snack("Привычка удалена", "info")

        self.confirm(
            "Удалить привычку?",
            f"Прогресс «{habit.title}» будет потерян.",
            action,
        )

    def quest_actions(self, quest: Quest) -> None:
        """Меню карточки квеста по долгому нажатию."""

        def edit() -> None:
            self.close_dialog()
            self.open_quest_dialog(quest)

        def remove() -> None:
            self.close_dialog()
            self.delete_quest(quest.id)

        self._open_actions(
            "Квест",
            quest.title,
            [
                ("Изменить", ft.Icons.EDIT_ROUNDED, t.TEXT, edit),
                ("Удалить", ft.Icons.DELETE_OUTLINE_ROUNDED, t.DANGER, remove),
            ],
            icon_data=ft.Icons.FLAG_ROUNDED,
        )

    def habit_actions(self, habit: Habit) -> None:
        """Меню карточки привычки по долгому нажатию."""

        def edit() -> None:
            self.close_dialog()
            self.open_habit_dialog(habit)

        def remove() -> None:
            self.close_dialog()
            self.delete_habit(habit.id)

        self._open_actions(
            "Привычка",
            habit.title,
            [
                ("Изменить", ft.Icons.EDIT_ROUNDED, t.TEXT, edit),
                ("Удалить", ft.Icons.DELETE_OUTLINE_ROUNDED, t.DANGER, remove),
            ],
            icon_data=ft.Icons.LOOP_ROUNDED,
        )

    def reward_actions(self, reward: Reward) -> None:
        """Меню карточки награды по долгому нажатию."""

        def edit() -> None:
            self.close_dialog()
            self.open_reward_dialog(reward)

        def remove() -> None:
            self.close_dialog()
            self.delete_reward(reward.id)

        self._open_actions(
            "Награда",
            reward.title,
            [
                ("Изменить", ft.Icons.EDIT_ROUNDED, t.TEXT, edit),
                (
                    "Удалить",
                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                    t.DANGER,
                    remove,
                ),
            ],
            icon_data=ft.Icons.REDEEM_ROUNDED,
            icon_color=t.GOLD,
        )

    def download_save(self) -> None:
        """Скачать текущее сохранение в JSON-файл."""
        self.page.run_task(self._download_save)

    async def _download_save(self) -> None:
        payload = save_bytes(self.state)
        try:
            result = await self.file_picker.save_file(
                dialog_title="Скачать сохранение",
                file_name=f"irl_quests_{date.today().isoformat()}.json",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                src_bytes=payload,
            )
        except Exception as exc:  # noqa: BLE001 — показываем причину пользователю
            self.show_snack(f"Не удалось скачать сохранение: {exc}", "error")
            return
        if result:
            self.show_snack("Сохранение скачано", "info")

    def import_save_result(self, e: ft.FilePickerResultEvent) -> None:
        """Обработать файл, выбранный кнопкой «Загрузить»."""
        if not e.files:
            return
        picked = e.files[0]
        raw = picked.bytes
        if raw is None and picked.path:
            try:
                with Path(picked.path).open("rb") as fh:
                    raw = fh.read(MAX_SAVE_SIZE + 1)
            except OSError as exc:
                self.show_snack(f"Не удалось прочитать файл: {exc}", "error")
                return
        if not raw:
            self.show_snack("Не удалось прочитать файл сохранения", "error")
            return
        try:
            imported = state_from_bytes(raw)
        except ValueError as exc:
            self.show_snack(f"Не удалось загрузить сохранение: {exc}", "error")
            return

        def action() -> None:
            # Подтверждение уже закрыто; здесь закрываем сами настройки,
            # потому что они построены по прежнему состоянию.
            self.close_dialog()
            self.state = imported
            self.state.add_log("info", "Прогресс загружен из файла")
            self.persist()
            self.show_snack("Сохранение загружено", "info")

        self.confirm(
            "Загрузить сохранение?",
            "Текущий прогресс, квесты и награды будут заменены данными из файла. "
            "Это действие нельзя отменить.",
            action,
            danger=False,
            ok_label="Загрузить",
        )

    def open_settings(self) -> None:
        name = t.text_field("Имя героя", value=self.state.player.name)

        def save_name() -> None:
            cleaned = (name.value or "").strip()
            if cleaned:
                self.state.player.name = cleaned
                self.state.add_log("info", f"Имя изменено на «{cleaned}»")
            self.close_dialog()
            self.persist()
            self.show_snack("Настройки сохранены", "info")

        def reset_progress() -> None:
            def action() -> None:
                self.state = self.storage.reset()
                self.persist()
                self.show_snack("Прогресс сброшен. Новая жизнь!", "info")

            self.confirm(
                "Начать заново?",
                "Весь прогресс, квесты и награды будут удалены.",
                action,
            )

        content = ft.Column(
            [
                name,
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Резервная копия", size=12, color=t.MUTED),
                            ft.Text(
                                "Скачайте файл прогресса или загрузите его на этом "
                                "или другом устройстве.",
                                size=11,
                                color=t.DIM,
                            ),
                            ft.Row(
                                [
                                    t.ghost_button(
                                        "Скачать",
                                        self.download_save,
                                        color=t.ACCENT,
                                    ),
                                    ft.TextButton(
                                        content="Загрузить",
                                        style=ft.ButtonStyle(
                                            color=t.ACCENT,
                                            shape=ft.RoundedRectangleBorder(radius=12),
                                            padding=ft.Padding.symmetric(
                                                horizontal=12, vertical=10
                                            ),
                                        ),
                                        action=ft.PickFiles(
                                            self.file_picker,
                                            dialog_title="Загрузить сохранение",
                                            file_type=ft.FilePickerFileType.CUSTOM,
                                            allowed_extensions=["json"],
                                            with_data=True,
                                        ),
                                    ),
                                ],
                                spacing=8,
                                tight=True,
                            ),
                        ],
                        spacing=8,
                        tight=True,
                    ),
                    padding=10,
                    bgcolor=t.SURFACE_2,
                    border_radius=12,
                ),
                ft.Text("Разработчик", size=12, weight=ft.FontWeight.W_600, color=t.MUTED),
                *[
                    ft.Row(
                        [
                            ft.Icon(icon, size=16, color=t.MUTED),
                            ft.Text(value, size=13, color=t.TEXT, selectable=True, expand=True),
                        ],
                        spacing=8,
                    )
                    for icon, value in (
                        (ft.Icons.SEND_ROUNDED, "@Lostor"),
                        (ft.Icons.MAIL_OUTLINE_ROUNDED, "lostor@1hokage.ru"),
                        (ft.Icons.CODE_ROUNDED, "https://github.com/Lstrzz"),
                    )
                ],
                ft.Row(
                    [
                        ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=16, color=t.MUTED),
                        ft.Text(
                            "IRL Quests · версия 1.2 · данные хранятся только на устройстве",
                            size=11,
                            color=t.DIM,
                            expand=True,
                        ),
                    ],
                    spacing=6,
                ),
                ft.Divider(height=1, color=t.BORDER),
                ft.TextButton(
                    content=ft.Text("Сбросить прогресс", size=13, color=t.DANGER),
                    icon=ft.Icons.RESTART_ALT_ROUNDED,
                    icon_color=t.DANGER,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding.symmetric(horizontal=8, vertical=10),
                    ),
                    on_click=lambda e: reset_progress(),
                ),
            ],
            spacing=14,
            tight=True,
        )

        self.page.show_dialog(
            t.dialog_shell(
                "Настройки",
                content,
                self._dialog_actions(save_name),
                icon_data=ft.Icons.SETTINGS_ROUNDED,
            )
        )
