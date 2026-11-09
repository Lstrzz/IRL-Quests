from __future__ import annotations

from datetime import date, timedelta

from app import engine
from app.models import Habit, Quest, default_state, level_title, xp_for_level
from app.storage import (
    MAX_SAVE_SIZE,
    Storage,
    save_bytes,
    state_from_bytes,
    state_from_dict,
    state_to_dict,
)


def test_level_curve() -> None:
    assert xp_for_level(1) == 0
    assert xp_for_level(2) == 100
    assert xp_for_level(3) == 300
    assert xp_for_level(4) == 600


def test_level_titles_change_every_ten_levels() -> None:
    assert level_title(1) == "Новичок"
    assert level_title(10) == "Новичок"
    assert level_title(11) == "Ученик"
    assert level_title(20) == "Ученик"
    assert level_title(21) == "Искатель"
    assert level_title(71) == "Герой"
    assert level_title(80) == "Герой"
    assert level_title(81) == "Хранитель"
    assert level_title(90) == "Хранитель"
    assert level_title(91) == "Легенда"
    assert level_title(100) == "Легенда"
    assert level_title(101) == "Легенда II"
    assert level_title(111) == "Легенда III"


def test_achievement_catalog_matches_checks() -> None:
    ids = {ach.id for ach in default_state().achievements}
    assert ids == set(engine.ACHIEVEMENT_CHECKS)
    assert len(ids) >= 40
    assert len(ids) == len(default_state().achievements)


def test_rank_achievements_unlock_at_their_levels() -> None:
    state = default_state()
    state.player.xp = xp_for_level(71)
    engine._check_achievements(state)

    assert state.achievement_by_id("level_71").unlocked_at
    assert not state.achievement_by_id("level_81").unlocked_at

    state.player.xp = xp_for_level(101)
    events = engine._check_achievements(state)

    assert state.achievement_by_id("level_81").unlocked_at
    assert state.achievement_by_id("level_91").unlocked_at
    assert state.achievement_by_id("level_101").unlocked_at
    assert any(e.kind == "achievement" for e in events)


def test_adding_quest_unlocks_planner() -> None:
    state = default_state()
    while len(state.quests) < 9:
        state.quests.append(Quest(title="Запасной квест"))

    events = engine.add_quest(state, Quest(title="Десятый квест"))

    assert state.achievement_by_id("planner_10").unlocked_at
    assert any(e.kind == "achievement" for e in events)


def test_shield_opacity_grows_to_full_by_30_days() -> None:
    assert engine.shield_opacity(0) == 0.25
    assert engine.shield_opacity(15) == 0.625
    assert engine.shield_opacity(engine.SHIELD_FULL_DAYS) == 1.0
    assert engine.shield_opacity(365) == 1.0
    assert engine.shield_opacity(-5) == 0.25


def test_flame_grows_during_first_month_after_shield() -> None:
    assert engine.flame_progress(0) == 0.0
    assert engine.flame_progress(engine.SHIELD_FULL_DAYS) == 0.0
    assert engine.flame_progress(45) == 0.5
    assert engine.flame_progress(engine.FLAME_FULL_DAYS) == 1.0
    assert engine.flame_progress(5000) == 1.0


def test_flame_changes_color_every_month_after_growth() -> None:
    colors = engine.FLAME_COLORS
    full = engine.FLAME_FULL_DAYS
    month = engine.FLAME_COLOR_MONTH_DAYS

    assert engine.flame_color(engine.SHIELD_FULL_DAYS) == colors[0]
    assert engine.flame_color(full) == colors[0]
    assert engine.flame_color(full + month) == colors[1]
    assert engine.flame_color(full + 2 * month) == colors[2]

    midpoint = engine.flame_color(full + month // 2)
    assert midpoint not in (colors[0], colors[1])
    assert midpoint.startswith("#") and len(midpoint) == 7

    cycle = full + len(colors) * month
    assert engine.flame_color(cycle) == colors[0]


def test_default_state_has_content() -> None:
    state = default_state()
    assert state.quests
    assert state.habits
    assert state.rewards
    assert state.achievements
    assert state.player.level == 1


def test_complete_daily_quest_once_per_day() -> None:
    state = default_state()
    quest = state.quests[0]
    xp_before = state.player.xp

    events = engine.complete_quest(state, quest.id)

    assert state.player.xp == xp_before + quest.xp
    assert state.stats.quests_done == 1
    assert any(e.kind == "achievement" for e in events)

    again = engine.complete_quest(state, quest.id)
    assert again[0].kind == "error"
    assert state.stats.quests_done == 1


def test_once_quest_disappears_after_completion() -> None:
    quest = Quest(title="Разовое дело", repeat="once")

    assert quest.is_available_today()
    quest.completed_on.append(date.today().isoformat())
    assert not quest.is_available_today()


def test_today_quests_include_pending_once_quests() -> None:
    state = default_state()
    once = Quest(title="Разовое дело", repeat="once")
    state.quests.append(once)

    assert once.id in [q.id for q in engine.today_quests(state)]

    once.completed_on.append(date.today().isoformat())
    assert once.id not in [q.id for q in engine.today_quests(state)]

    daily = next(q for q in state.quests if q.repeat == "daily")
    daily.completed_on.append(date.today().isoformat())
    assert daily.id in [q.id for q in engine.today_quests(state)]


def test_today_progress_counts_pending_once_quests() -> None:
    state = default_state()
    done_before, total_before = engine.today_progress(state)
    once = Quest(title="Разовое дело", repeat="once")
    state.quests.append(once)

    done, total = engine.today_progress(state)
    assert (done, total) == (done_before, total_before + 1)

    engine.complete_quest(state, once.id)
    assert engine.today_progress(state) == (done_before, total_before)


def test_level_up_gives_bonus() -> None:
    state = default_state()
    state.player.xp = 95
    state.player.coins = 0
    quest = Quest(title="Почти уровень", difficulty="easy", repeat="once")
    state.quests.append(quest)

    events = engine.complete_quest(state, quest.id)

    assert state.player.level == 2
    assert any(e.kind == "levelup" for e in events)
    assert state.player.coins >= quest.coins + 50


def test_habit_streak_continues() -> None:
    state = default_state()
    habit = Habit(title="Тест")
    habit.last_done = (date.today() - timedelta(days=1)).isoformat()
    habit.streak = 2
    state.habits.append(habit)

    engine.check_in_habit(state, habit.id)

    assert habit.streak == 3
    assert habit.best_streak == 3
    assert habit.done_today()


def test_habit_streak_resets_after_gap() -> None:
    state = default_state()
    habit = Habit(title="Тест")
    habit.last_done = (date.today() - timedelta(days=3)).isoformat()
    habit.streak = 7
    habit.best_streak = 7
    state.habits.append(habit)

    engine.check_in_habit(state, habit.id)

    assert habit.streak == 1
    assert habit.best_streak == 7


def test_habit_check_in_twice_same_day_is_noop() -> None:
    state = default_state()
    habit = state.habits[0]

    engine.check_in_habit(state, habit.id)
    streak = habit.streak
    engine.check_in_habit(state, habit.id)

    assert habit.streak == streak
    assert state.stats.habits_done == 1


def test_positive_habit_boosts_quest_rewards_for_the_day() -> None:
    state = default_state()
    quest = Quest(title="Тест", difficulty="normal")
    state.quests.append(quest)
    habit = Habit(title="Позитив", difficulty="hard")
    state.habits.append(habit)
    habit.mark_done()

    xp_before, coins_before = state.stats.xp_earned, state.stats.coins_earned
    engine.complete_quest(state, quest.id)

    assert state.stats.xp_earned - xp_before == round(quest.xp * 1.20)
    assert state.stats.coins_earned - coins_before == round(quest.coins * 1.20)


def test_negative_habit_gives_no_xp_and_reduces_rewards() -> None:
    state = default_state()
    bad = Habit(title="Срыв", difficulty="normal", kind="negative")
    state.habits.append(bad)
    xp_before = state.player.xp

    engine.check_in_habit(state, bad.id)
    assert bad.done_today()
    assert bad.streak == 0
    assert state.player.xp == xp_before
    assert state.stats.habits_done == 0

    quest = Quest(title="Тест", difficulty="normal")
    state.quests.append(quest)
    xp_before = state.stats.xp_earned
    engine.complete_quest(state, quest.id)
    assert state.stats.xp_earned - xp_before == round(quest.xp * 0.90)


def test_negative_habit_second_mark_same_day_is_noop() -> None:
    state = default_state()
    bad = Habit(title="Срыв", kind="negative")
    state.habits.append(bad)

    engine.check_in_habit(state, bad.id)
    events = engine.check_in_habit(state, bad.id)

    assert events[0].kind == "info"
    assert engine.day_multiplier(state) == 0.9


def test_relapse_achievements_count_honest_marks_and_clean_days() -> None:
    state = default_state()
    bad = Habit(title="Срыв", kind="negative")
    state.habits.append(bad)

    engine.check_in_habit(state, bad.id)
    assert state.stats.relapses == 1
    assert state.achievement_by_id("relapse_1").unlocked_at
    assert state.achievement_by_id("negative_3").unlocked_at is None

    bad.last_done = (date.today() - timedelta(days=8)).isoformat()
    engine._check_achievements(state)
    assert state.achievement_by_id("clean_7").unlocked_at
    assert state.achievement_by_id("clean_30").unlocked_at is None

    bad.last_done = (date.today() - timedelta(days=31)).isoformat()
    engine._check_achievements(state)
    assert state.achievement_by_id("clean_30").unlocked_at
    assert state.achievement_by_id("clean_365").unlocked_at is None

    bad.last_done = (date.today() - timedelta(days=365)).isoformat()
    engine._check_achievements(state)
    assert state.achievement_by_id("clean_365").unlocked_at


def test_day_multiplier_is_clamped_between_half_and_double() -> None:
    state = default_state()
    for _ in range(5):
        h = Habit(title="Срыв", difficulty="epic", kind="negative")
        state.habits.append(h)
        h.mark_done()
    assert engine.day_multiplier(state) == 0.5

    state = default_state()
    for _ in range(10):
        h = Habit(title="Плюс", difficulty="epic")
        state.habits.append(h)
        h.mark_done()
    assert engine.day_multiplier(state) == 2.0


def test_habit_kind_survives_save_and_legacy_saves_default_to_positive() -> None:
    state = default_state()
    state.habits[0].kind = "negative"
    restored = state_from_dict(state_to_dict(state))
    assert restored.habits[0].is_negative

    legacy = state_to_dict(state)
    for raw in legacy["habits"]:
        raw.pop("kind", None)
    assert all(not h.is_negative for h in state_from_dict(legacy).habits)


def test_update_quest_keeps_history_and_changes_fields() -> None:
    state = default_state()
    quest = state.quests[0]
    engine.complete_quest(state, quest.id)
    done_on = list(quest.completed_on)
    created = quest.created_at

    engine.update_quest(
        state,
        quest.id,
        title="Новое имя",
        description="Новое описание",
        attribute="strength",
        difficulty="epic",
        repeat="weekly",
        icon="fitness_center",
    )

    assert quest.title == "Новое имя"
    assert quest.attribute == "strength"
    assert quest.difficulty == "epic"
    assert quest.repeat == "weekly"
    assert quest.icon == "fitness_center"
    assert quest.completed_on == done_on
    assert quest.created_at == created


def test_update_quest_rejects_unknown_id_and_keeps_title() -> None:
    state = default_state()
    quest = state.quests[0]
    old_title = quest.title

    events = engine.update_quest(
        state, "missing", title="x", description="", attribute="will",
        difficulty="normal", repeat="daily", icon="flag",
    )
    assert events[0].kind == "error"

    engine.update_quest(
        state, quest.id, title="   ", description="", attribute="will",
        difficulty="normal", repeat="daily", icon="flag",
    )
    assert quest.title == old_title


def test_habit_difficulty_changes_reward() -> None:
    state = default_state()
    easy = Habit(title="Легко", difficulty="easy")
    epic = Habit(title="Эпично", difficulty="epic")
    state.habits.extend([easy, epic])

    xp_before = state.player.xp
    engine.check_in_habit(state, easy.id)
    easy_xp = state.player.xp - xp_before

    xp_before = state.player.xp
    engine.check_in_habit(state, epic.id)
    epic_xp = state.player.xp - xp_before

    # бонус за первый день серии, умноженный на коэффициент дня от отметки
    assert easy_xp == round((easy.base_xp + 2) * 1.05)
    assert epic_xp == round((epic.base_xp + 2) * 1.35)
    assert epic_xp > easy_xp


def test_update_habit_keeps_streak_and_changes_difficulty() -> None:
    state = default_state()
    habit = Habit(title="Старое имя", attribute="will", difficulty="easy")
    habit.streak = 5
    state.habits.append(habit)

    engine.update_habit(
        state,
        habit.id,
        title="Новое имя",
        attribute="strength",
        difficulty="hard",
        icon="fitness_center",
    )

    assert habit.title == "Новое имя"
    assert habit.attribute == "strength"
    assert habit.difficulty == "hard"
    assert habit.icon == "fitness_center"
    assert habit.streak == 5


def test_reward_cannot_be_bought_without_coins() -> None:
    state = default_state()
    state.player.coins = 0
    reward = state.rewards[0]

    events = engine.buy_reward(state, reward.id)

    assert events[0].kind == "error"
    assert state.player.coins == 0
    assert reward.purchases == 0


def test_reward_purchase_spends_coins() -> None:
    state = default_state()
    reward = state.rewards[0]
    state.player.coins = reward.cost + 10

    engine.buy_reward(state, reward.id)

    assert state.player.coins == 10
    assert reward.purchases == 1
    assert state.stats.rewards_bought == 1


def test_buy_reward_quantity_spends_total_and_fills_inventory() -> None:
    state = default_state()
    reward = state.rewards[0]
    state.player.coins = reward.cost * 3

    engine.buy_reward(state, reward.id, 3)

    assert state.player.coins == 0
    assert reward.owned == 3
    assert reward.purchases == 3
    assert state.stats.rewards_bought == 3
    assert engine.inventory(state) == [reward]


def test_buy_reward_quantity_fails_without_enough_coins() -> None:
    state = default_state()
    reward = state.rewards[0]
    state.player.coins = reward.cost * 2

    events = engine.buy_reward(state, reward.id, 3)

    assert events[0].kind == "error"
    assert state.player.coins == reward.cost * 2
    assert reward.owned == 0


def test_use_reward_takes_from_inventory_and_removes_empty_items() -> None:
    state = default_state()
    reward = state.rewards[0]
    reward.owned = 3

    engine.use_reward(state, reward.id, 2)
    assert reward.owned == 1
    assert engine.inventory(state) == [reward]

    engine.use_reward(state, reward.id, 5)
    assert reward.owned == 0
    assert engine.inventory(state) == []


def test_use_reward_without_inventory_is_error() -> None:
    state = default_state()
    reward = state.rewards[0]

    events = engine.use_reward(state, reward.id)

    assert events[0].kind == "error"
    assert reward.owned == 0


def test_bulk_purchase_and_inventory_unlock_achievements() -> None:
    state = default_state()
    reward = state.rewards[0]
    state.player.coins = reward.cost * 5

    engine.buy_reward(state, reward.id, 5)

    assert state.achievement_by_id("bulk_buy").unlocked_at
    assert state.achievement_by_id("inventory_5").unlocked_at


def test_using_rewards_unlocks_usage_achievements() -> None:
    state = default_state()
    reward = state.rewards[0]
    reward.owned = 10

    events = engine.use_reward(state, reward.id, 1)
    assert state.achievement_by_id("rewards_used_1").unlocked_at
    assert any(e.kind == "achievement" for e in events)
    assert not state.achievement_by_id("rewards_used_10").unlocked_at

    engine.use_reward(state, reward.id, 9)
    assert state.stats.rewards_used == 10
    assert state.achievement_by_id("rewards_used_10").unlocked_at


def test_inventory_survives_save_and_old_saves_default_to_zero() -> None:
    state = default_state()
    state.rewards[0].owned = 2
    restored = state_from_dict(state_to_dict(state))
    assert restored.rewards[0].owned == 2

    legacy = state_to_dict(state)
    for raw in legacy["rewards"]:
        raw.pop("owned", None)
    assert all(r.owned == 0 for r in state_from_dict(legacy).rewards)


def test_update_reward_changes_title_and_cost() -> None:
    state = default_state()
    reward = state.rewards[0]
    reward_id = reward.id
    purchases = reward.purchases

    engine.update_reward(state, reward.id, title="Новая награда", cost=250)

    updated = state.reward_by_id(reward_id)
    assert updated is not None
    assert updated.title == "Новая награда"
    assert updated.cost == 250
    assert updated.purchases == purchases
    assert updated.id == reward_id


def test_update_reward_changes_icon_and_keeps_it_when_not_given() -> None:
    state = default_state()
    reward = state.rewards[0]

    engine.update_reward(state, reward.id, title=reward.title, cost=reward.cost, icon="cake")
    assert reward.icon == "cake"

    engine.update_reward(state, reward.id, title="Иное", cost=reward.cost)
    assert reward.icon == "cake"


def test_update_reward_keeps_minimum_cost_and_rejects_unknown_id() -> None:
    state = default_state()
    reward = state.rewards[0]

    engine.update_reward(state, reward.id, title="  ", cost=0)
    assert reward.title
    assert reward.cost == 1

    engine.update_reward(state, "missing", title="Нет", cost=10)
    assert state.reward_by_id("missing") is None


def test_delete_reward_keeps_other_rewards() -> None:
    state = default_state()
    removed = state.rewards[0]
    remaining = [reward.id for reward in state.rewards[1:]]

    engine.delete_reward(state, removed.id)

    assert state.reward_by_id(removed.id) is None
    assert [reward.id for reward in state.rewards] == remaining


def test_storage_roundtrip(tmp_path) -> None:
    storage = Storage(tmp_path)
    state = default_state()
    state.player.name = "Тестовый герой"
    state.player.xp = 123
    state.quests[0].completed_on.append(date.today().isoformat())

    storage.save(state)
    loaded = storage.load()

    assert loaded.player.name == "Тестовый герой"
    assert loaded.player.xp == 123
    assert loaded.quests[0].id == state.quests[0].id
    assert loaded.quests[0].completed_on == state.quests[0].completed_on
    assert loaded.achievements[-1].id == state.achievements[-1].id


def test_legacy_achievement_texts_are_refreshed(tmp_path) -> None:
    storage = Storage(tmp_path)
    state = default_state()
    legacy = state.achievement_by_id("level_3")
    legacy.title = "Искатель"
    legacy.description = "Старое условие"
    legacy.unlocked_at = "2026-01-01"
    storage.save(state)

    loaded = storage.load()
    ach = loaded.achievement_by_id("level_3")

    assert ach.title == "В пути"
    assert ach.description == "Достигни 3 уровня"
    assert ach.unlocked_at == "2026-01-01"
    assert loaded.achievement_by_id("level_101") is not None


def test_broken_save_is_recovered(tmp_path) -> None:
    storage = Storage(tmp_path)
    storage.directory.mkdir(parents=True, exist_ok=True)
    storage.path.write_text("{ definitely not json", encoding="utf-8")

    state = storage.load()

    assert state.quests
    assert storage.path.exists()


def test_state_dict_is_json_safe() -> None:
    state = default_state()
    restored = state_from_dict(state_to_dict(state))

    assert restored.player.xp == state.player.xp
    assert len(restored.quests) == len(state.quests)
    assert len(restored.habits) == len(state.habits)
    assert restored.attributes == state.attributes


def test_save_bytes_roundtrip() -> None:
    state = default_state()
    state.player.name = "Экспортированный герой"
    state.player.coins = 321
    state.quests[0].completed_on.append(date.today().isoformat())

    restored = state_from_bytes(save_bytes(state))

    assert restored.player.name == "Экспортированный герой"
    assert restored.player.coins == 321
    assert restored.quests[0].completed_on == state.quests[0].completed_on
    assert restored.achievements


def test_state_from_bytes_rejects_foreign_files() -> None:
    for payload in (
        b"",
        b"{ definitely not json",
        b"[]",
        b'{"foo": 1}',
        b'{"player": "not a dict"}',
        b'{"player": {"xp": "oops"}}',
    ):
        try:
            state_from_bytes(payload)
        except ValueError:
            continue
        raise AssertionError(f"payload accepted: {payload!r}")


def test_state_from_bytes_rejects_oversized_file() -> None:
    try:
        state_from_bytes(b" " * (MAX_SAVE_SIZE + 1))
    except ValueError:
        return
    raise AssertionError("oversized payload accepted")


def test_habit_difficulty_survives_save_and_legacy_saves_default_to_normal() -> None:
    state = default_state()
    restored = state_from_dict(state_to_dict(state))
    assert [h.difficulty for h in restored.habits] == [
        h.difficulty for h in state.habits
    ]

    legacy = state_to_dict(state)
    for raw in legacy["habits"]:
        raw.pop("difficulty", None)
    restored_legacy = state_from_dict(legacy)
    assert all(h.difficulty == "normal" for h in restored_legacy.habits)
