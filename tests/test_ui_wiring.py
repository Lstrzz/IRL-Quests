"""Проверка связей интерфейса: экраны не должны звать несуществующие методы."""

from __future__ import annotations

import re
from pathlib import Path

import flet as ft
import pytest

from app.models import DIFFICULTIES, Habit, default_state
from app.storage import Storage, save_bytes
from app.ui import theme as t
from app.ui.app import IRLApp
from app.ui.components import (
    CARD_BORDER_ALPHA,
    HABIT_ICON_CHOICES,
    HABIT_ICON_GROUPS,
    ICON_BG_ALPHA,
    QUEST_ICON_CHOICES,
    QUEST_ICON_GROUPS,
    REWARD_ICON_CHOICES,
    REWARD_ICON_GROUPS,
    IconPicker,
    QuantityStepper,
    inventory_card,
    _check_button,
    _done_mark,
    habit_card,
    quest_card,
    reward_card,
)

VIEWS_DIR = Path(__file__).resolve().parents[1] / "src" / "app" / "ui" / "views"
# Атрибуты, которые создаются в IRLApp.__init__, а не объявлены методами.
INSTANCE_ATTRS = {"state", "quest_filter"}


def test_views_only_call_existing_app_members() -> None:
    used: set[str] = set()
    for path in VIEWS_DIR.glob("*.py"):
        used.update(re.findall(r"self\.app\.([A-Za-z_][A-Za-z0-9_]*)", path.read_text("utf-8")))

    missing = used - INSTANCE_ATTRS - set(dir(IRLApp))
    assert not missing, f"Экраны вызывают несуществующие методы IRLApp: {sorted(missing)}"


def test_cards_open_actions_on_long_press() -> None:
    state = default_state()
    calls: list[str] = []

    def actions(name: str):
        return lambda: calls.append(name)

    cards = {
        "quest": quest_card(
            state.quests[0],
            on_complete=lambda: None,
            on_actions=actions("quest"),
        ),
        "habit": habit_card(
            state.habits[0],
            on_check_in=lambda: None,
            on_actions=actions("habit"),
        ),
        "reward": reward_card(
            state.rewards[0],
            coins=0,
            on_buy=lambda: None,
            on_actions=actions("reward"),
        ),
    }

    for name, card in cards.items():
        assert isinstance(card, ft.GestureDetector)
        assert card.on_long_press is not None
        assert card.on_secondary_tap is not None
        card.on_long_press(None)
        assert calls[-1] == name


@pytest.mark.parametrize(
    "choices",
    [QUEST_ICON_CHOICES, HABIT_ICON_CHOICES, REWARD_ICON_CHOICES],
    ids=["quest", "habit", "reward"],
)
def test_icon_pools_exist_in_flet_and_have_no_duplicates(choices: list[str]) -> None:
    missing = [name for name in choices if not hasattr(ft.Icons, name.upper())]
    assert not missing, f"Нет таких значков во Flet: {missing}"
    assert len(choices) == len(set(choices))


def test_quantity_stepper_limits_and_inventory_card_open_handler() -> None:
    stepper = QuantityStepper(maximum=3)
    assert stepper.value == 1
    assert stepper._minus.disabled is True
    assert stepper._plus.disabled is False

    single = QuantityStepper(maximum=1)
    assert single._minus.disabled is True
    assert single._plus.disabled is True

    opened: list[str] = []
    card = inventory_card(
        default_state().rewards[0],
        on_open=lambda: opened.append("open"),
    )
    button = card.content.controls[-1]
    assert isinstance(button, ft.Button)
    assert button.content == "Использовать"
    button.on_click(None)
    assert opened == ["open"]


def test_icon_picker_highlights_only_selected_icon() -> None:
    picker = IconPicker(REWARD_ICON_GROUPS, "tv", t.GOLD)

    assert picker.value == "tv"
    assert picker.group == "Отдых"
    assert picker.tiles["tv"].bgcolor == ft.Colors.with_opacity(ICON_BG_ALPHA, t.GOLD)
    others = [tile for name, tile in picker.tiles.items() if name != "tv"]
    assert all(tile.bgcolor is None for tile in others)


def test_icon_picker_categories_wrap_instead_of_scrolling() -> None:
    picker = IconPicker(REWARD_ICON_GROUPS, "tv", t.GOLD)

    assert picker._chip_row.wrap is True
    assert picker._chip_row.scroll is None
    assert picker._tile_row.wrap is True


def test_icon_picker_keeps_unknown_current_icon() -> None:
    picker = IconPicker(REWARD_ICON_GROUPS, "groups", t.GOLD)

    assert "groups" in picker.tiles
    assert picker.value == "groups"
    assert picker.group == "Прочее"


@pytest.mark.parametrize(
    "groups",
    [QUEST_ICON_GROUPS, HABIT_ICON_GROUPS, REWARD_ICON_GROUPS],
    ids=["quest", "habit", "reward"],
)
def test_icon_groups_have_four_icons_each_for_phone_row(groups: dict[str, list[str]]) -> None:
    assert all(len(icons) == 4 for icons in groups.values())


def test_check_button_starts_empty_and_gains_a_check() -> None:
    empty = _check_button(lambda: None, t.PINK)
    done = _done_mark()

    assert empty.border_radius == 22
    assert done.border_radius == 22
    assert empty.content is None
    assert empty.bgcolor is None
    assert empty.border.top.color == ft.Colors.with_opacity(
        CARD_BORDER_ALPHA, t.PINK
    )
    # Отметка всегда зелёная, независимо от цвета характеристики.
    assert done.bgcolor == ft.Colors.with_opacity(ICON_BG_ALPHA, t.ACCENT)
    assert done.border.top.color == ft.Colors.with_opacity(
        CARD_BORDER_ALPHA, t.ACCENT
    )
    assert isinstance(done.content, ft.Icon)
    assert done.content.icon == ft.Icons.CHECK_ROUNDED
    assert done.content.color == t.ACCENT


def test_quest_card_border_and_icon_follow_attribute_without_glow() -> None:
    quest = default_state().quests[0]
    card = quest_card(
        quest,
        on_complete=lambda: None,
        on_actions=lambda: None,
    )

    panel = card.content
    assert isinstance(panel, ft.Container)
    assert panel.shadow is None
    assert panel.border is not None
    assert panel.border.top.color == ft.Colors.with_opacity(
        CARD_BORDER_ALPHA, t.attr_color(quest.attribute)
    )

    leading = panel.content.controls[0]
    assert leading.shadow is None
    assert leading.content.color == t.attr_color(quest.attribute)


def test_quest_card_shows_difficulty_tag_without_xp_and_coins_tags() -> None:
    quest = default_state().quests[0]
    card = quest_card(
        quest,
        on_complete=lambda: None,
        on_actions=lambda: None,
    )

    meta = card.content.content.controls[1].controls[-1]
    labels = [
        control.content.controls[-1].value
        for control in meta.controls
        if isinstance(control, ft.Container)
    ]
    assert labels == [DIFFICULTIES[quest.difficulty][0]]
    assert all("XP" not in label for label in labels)


def test_dashboard_builds_with_positive_and_negative_habits() -> None:
    from unittest.mock import MagicMock

    from app.ui.views.dashboard import DashboardView

    state = default_state()
    state.habits.append(Habit(title="Срыв", kind="negative"))
    app = MagicMock()
    app.state = state

    assert isinstance(DashboardView(app).build(), ft.Column)


def test_dashboard_greeting_allows_wrapping() -> None:
    from unittest.mock import MagicMock

    from app.ui.views.dashboard import DashboardView

    state = default_state()
    state.player.name = "Очень длинное имя странника"
    app = MagicMock()
    app.state = state

    texts = [c for c in _walk(DashboardView(app).build()) if isinstance(c, ft.Text)]
    greeting = next(c for c in texts if c.value and c.value.endswith("!"))

    assert greeting.max_lines is None
    assert greeting.overflow != ft.TextOverflow.ELLIPSIS


def test_habits_view_builds_two_groups_with_effect_legend() -> None:
    from unittest.mock import MagicMock

    from app.ui.views.habits import HabitsView

    state = default_state()
    state.habits.append(Habit(title="Срыв", kind="negative"))
    app = MagicMock()
    app.state = state

    view = HabitsView(app).build()
    assert isinstance(view, ft.Column)
    texts = [c.value for c in _walk(view) if isinstance(c, ft.Text)]
    assert "Позитивные" in texts
    assert "Негативные" in texts
    assert "Заработок дня от привычек" in texts


def _walk(control):
    yield control
    children = getattr(control, "controls", None) or []
    if getattr(control, "content", None) is not None:
        children = [*children, control.content]
    for child in children:
        yield from _walk(child)


def test_dashboard_shows_buff_potion_only_when_day_effect_is_active() -> None:
    from unittest.mock import MagicMock

    from app.ui.views.dashboard import DashboardView

    state = default_state()
    app = MagicMock()
    app.state = state
    view = DashboardView(app)
    assert view._day_effect_badge(1.0) == []

    buff = view._day_effect_badge(1.10)
    assert buff and buff[0].tooltip == "Итог дня от привычек: +10% к заработку"
    assert buff[0].content.controls[0].color == t.ACCENT

    debuff = view._day_effect_badge(0.90)
    assert debuff and debuff[0].tooltip == "Итог дня от привычек: −10% к заработку"
    assert debuff[0].content.controls[0].color == t.DANGER

    habit = Habit(title="Плюс", difficulty="normal")
    state.habits.append(habit)
    habit.mark_done()
    texts = [c.value for c in _walk(DashboardView(app).build()) if isinstance(c, ft.Text)]
    assert "+10%" in texts


def test_hero_report_shows_achievement_count_and_app_has_export() -> None:
    from app.ui.report import build_hero_report

    state = default_state()
    state.achievements[0].unlocked_at = "2026-11-06"
    report = build_hero_report(state)
    texts = [c.value for c in _walk(report) if isinstance(c, ft.Text)]
    assert f"Достижения: 1 из {len(state.achievements)}" in texts
    assert hasattr(IRLApp, "open_report_dialog")


def test_settings_offers_save_export_and_import(tmp_path, monkeypatch) -> None:
    from unittest.mock import MagicMock

    monkeypatch.setenv("IRL_QUESTS_DATA_DIR", str(tmp_path))
    page = MagicMock()
    app = IRLApp(page)
    app.open_settings()

    dialog = page.show_dialog.call_args[0][0]
    buttons = [c for c in _walk(dialog) if isinstance(c, ft.TextButton)]
    by_label = {b.content: b for b in buttons if isinstance(b.content, str)}

    assert "Скачать" in by_label
    assert by_label["Скачать"].on_click is not None

    upload = by_label["Загрузить"]
    assert isinstance(upload.action, ft.PickFiles)
    assert upload.action.with_data is True
    assert upload.action.allowed_extensions == ["json"]


def test_import_save_replaces_state_after_confirmation(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    monkeypatch.setenv("IRL_QUESTS_DATA_DIR", str(tmp_path))
    page = MagicMock()
    app = IRLApp(page)
    app.state.player.name = "Старый"

    exported = default_state()
    exported.player.name = "Новый"
    exported.player.coins = 999
    event = SimpleNamespace(
        files=[SimpleNamespace(bytes=save_bytes(exported), path=None)]
    )

    app.import_save_result(event)

    confirm_dialog = page.show_dialog.call_args[0][0]
    assert confirm_dialog.title.value == "Загрузить сохранение?"
    assert app.state.player.name == "Старый"

    load_button = next(
        b
        for b in confirm_dialog.actions
        if isinstance(b, ft.Button) and b.content == "Загрузить"
    )
    app.refresh = lambda: None
    load_button.on_click(None)

    assert app.state.player.name == "Новый"
    assert app.state.player.coins == 999
    assert Storage(tmp_path).load().player.name == "Новый"


def test_import_save_rejects_broken_file(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    monkeypatch.setenv("IRL_QUESTS_DATA_DIR", str(tmp_path))
    page = MagicMock()
    app = IRLApp(page)
    app.state.player.name = "Старый"
    event = SimpleNamespace(
        files=[SimpleNamespace(bytes=b"definitely not json", path=None)]
    )

    app.import_save_result(event)

    snack = page.show_dialog.call_args[0][0]
    assert isinstance(snack, ft.SnackBar)
    assert app.state.player.name == "Старый"


def test_negative_habit_card_shows_warning_only_after_marking() -> None:
    bad = Habit(title="Срыв", kind="negative")
    card = habit_card(bad, on_check_in=lambda: None, on_actions=lambda: None)

    button = card.content.content.controls[-1]
    assert button.content is None
    assert button.bgcolor is None
    assert button.on_click is not None

    bad.mark_done()
    card = habit_card(bad, on_check_in=lambda: None, on_actions=lambda: None)
    button = card.content.content.controls[-1]
    assert button.content.icon == ft.Icons.WARNING_AMBER_ROUNDED
    assert button.bgcolor is not None
    assert button.on_click is None


def test_habit_card_uses_same_subtle_border_and_button_as_quest() -> None:
    state = default_state()
    habit = state.habits[0]
    quest = state.quests[0]

    habit_panel = habit_card(
        habit,
        on_check_in=lambda: None,
        on_actions=lambda: None,
    ).content
    quest_panel = quest_card(
        quest,
        on_complete=lambda: None,
        on_actions=lambda: None,
    ).content

    assert habit_panel.shadow is None
    assert habit_panel.border.top.color == ft.Colors.with_opacity(
        CARD_BORDER_ALPHA, t.attr_color(habit.attribute)
    )

    habit_button = habit_panel.content.controls[-1]
    quest_button = quest_panel.content.controls[-1]
    assert habit_button.border_radius == quest_button.border_radius == 22
    assert habit_button.bgcolor is None
    assert quest_button.bgcolor is None
    assert habit_button.content is None
    assert quest_button.content is None


def test_habit_card_shows_difficulty() -> None:
    habit = default_state().habits[0]
    card = habit_card(
        habit,
        on_check_in=lambda: None,
        on_actions=lambda: None,
    )

    meta = card.content.content.controls[1].controls[1]
    labels = [
        control.content.controls[-1].value
        for control in meta.controls
        if isinstance(control, ft.Container)
    ]
    assert habit.difficulty_name in labels
