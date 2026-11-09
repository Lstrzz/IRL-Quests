"""Игровые правила: опыт, уровни, серии, достижения.

Движок ничего не знает про интерфейс. Каждое действие возвращает список
событий (Event) — их удобно показывать пользователю в виде снекбаров.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .models import (
    ATTRIBUTES,
    DIFFICULTIES,
    GameState,
    Habit,
    Quest,
    Reward,
    today_iso,
    xp_for_level,
)


@dataclass
class Event:
    kind: str  # xp | levelup | achievement | coins | error | info
    text: str


# ---------------------------------------------------------------------------
# Достижения: id -> предикат от состояния
# ---------------------------------------------------------------------------

def _best_streak(state: GameState) -> int:
    return max((habit.best_streak for habit in state.habits), default=0)


def _any_attribute(state: GameState, value: int) -> bool:
    return any(state.attributes.get(code, 0) >= value for code in ATTRIBUTES)


def _all_attributes(state: GameState, value: int) -> bool:
    return all(state.attributes.get(code, 0) >= value for code in ATTRIBUTES)


ACHIEVEMENT_CHECKS = {
    # Квесты
    "first_step": lambda s: s.stats.quests_done >= 1,
    "quests_10": lambda s: s.stats.quests_done >= 10,
    "quests_25": lambda s: s.stats.quests_done >= 25,
    "quests_50": lambda s: s.stats.quests_done >= 50,
    "quests_100": lambda s: s.stats.quests_done >= 100,
    "quests_250": lambda s: s.stats.quests_done >= 250,
    "quests_500": lambda s: s.stats.quests_done >= 500,
    # Привычки
    "habits_1": lambda s: s.stats.habits_done >= 1,
    "habits_10": lambda s: s.stats.habits_done >= 10,
    "habits_50": lambda s: s.stats.habits_done >= 50,
    "habits_100": lambda s: s.stats.habits_done >= 100,
    "habits_250": lambda s: s.stats.habits_done >= 250,
    # Серии
    "streak_3": lambda s: _best_streak(s) >= 3,
    "streak_7": lambda s: _best_streak(s) >= 7,
    "streak_14": lambda s: _best_streak(s) >= 14,
    "streak_30": lambda s: _best_streak(s) >= 30,
    "streak_60": lambda s: _best_streak(s) >= 60,
    "streak_100": lambda s: _best_streak(s) >= 100,
    "streak_365": lambda s: _best_streak(s) >= 365,
    # Уровни и звания
    "level_3": lambda s: s.player.level >= 3,
    "level_5": lambda s: s.player.level >= 5,
    "level_10": lambda s: s.player.level >= 10,
    "level_21": lambda s: s.player.level >= 21,
    "level_41": lambda s: s.player.level >= 41,
    "level_61": lambda s: s.player.level >= 61,
    "level_71": lambda s: s.player.level >= 71,
    "level_81": lambda s: s.player.level >= 81,
    "level_91": lambda s: s.player.level >= 91,
    "level_101": lambda s: s.player.level >= 101,
    # Характеристики
    "balanced": lambda s: _all_attributes(s, 5),
    "attr_any_10": lambda s: _any_attribute(s, 10),
    "attr_any_25": lambda s: _any_attribute(s, 25),
    "attr_any_50": lambda s: _any_attribute(s, 50),
    "attr_all_10": lambda s: _all_attributes(s, 10),
    "attr_all_25": lambda s: _all_attributes(s, 25),
    # Опыт
    "xp_1000": lambda s: s.stats.xp_earned >= 1_000,
    "xp_10000": lambda s: s.stats.xp_earned >= 10_000,
    "xp_100000": lambda s: s.stats.xp_earned >= 100_000,
    "xp_500000": lambda s: s.stats.xp_earned >= 500_000,
    # Награды
    "rewards_1": lambda s: s.stats.rewards_bought >= 1,
    "collector": lambda s: s.stats.rewards_bought >= 3,
    "rewards_10": lambda s: s.stats.rewards_bought >= 10,
    "rewards_25": lambda s: s.stats.rewards_bought >= 25,
    "bulk_buy": lambda s: s.stats.biggest_purchase >= 5,
    "inventory_5": lambda s: sum(r.owned for r in s.rewards) >= 5,
    "rewards_used_1": lambda s: s.stats.rewards_used >= 1,
    "rewards_used_10": lambda s: s.stats.rewards_used >= 10,
    "rewards_used_25": lambda s: s.stats.rewards_used >= 25,
    "rewards_50": lambda s: s.stats.rewards_bought >= 50,
    "rewards_100": lambda s: s.stats.rewards_bought >= 100,
    "rewards_used_50": lambda s: s.stats.rewards_used >= 50,
    "rewards_used_100": lambda s: s.stats.rewards_used >= 100,
    "inventory_10": lambda s: sum(r.owned for r in s.rewards) >= 10,
    "inventory_20": lambda s: sum(r.owned for r in s.rewards) >= 20,
    "bulk_10": lambda s: s.stats.biggest_purchase >= 10,
    "negative_3": lambda s: sum(1 for h in s.habits if h.is_negative) >= 3,
    "relapse_1": lambda s: s.stats.relapses >= 1,
    "relapse_10": lambda s: s.stats.relapses >= 10,
    "clean_7": lambda s: _clean_days(s) >= 7,
    "clean_30": lambda s: _clean_days(s) >= 30,
    "clean_365": lambda s: _clean_days(s) >= 365,
    # Планирование
    "planner_10": lambda s: len(s.quests) >= 10,
    "planner_25": lambda s: len(s.quests) >= 25,
    "habit_maker_5": lambda s: len(s.habits) >= 5,
    "habit_maker_10": lambda s: len(s.habits) >= 10,
}


def _add_xp(state: GameState, xp: int, coins: int) -> list[Event]:
    """Начислить опыт и монеты, обработать повышение уровня."""
    events: list[Event] = []
    old_level = state.player.level

    state.player.xp += xp
    state.player.coins += coins
    state.stats.xp_earned += xp
    state.stats.coins_earned += coins

    if state.player.level > old_level:
        bonus = 25 * state.player.level
        state.player.coins += bonus
        state.stats.coins_earned += bonus
        events.append(
            Event("levelup", f"Уровень {state.player.level}! Бонус: +{bonus} монет")
        )

    return events


def _clean_days(state: GameState) -> int:
    """Дни без срыва: максимум дней с последнего срыва среди негативных привычек."""
    days = [
        h.days_since_last()
        for h in state.habits
        if h.is_negative and h.days_since_last() is not None
    ]
    return max(days, default=0)


def _check_achievements(state: GameState) -> list[Event]:
    """Разблокировать все достижения, условия которых выполнены."""
    events: list[Event] = []
    for ach in state.achievements:
        if ach.unlocked_at:
            continue
        check = ACHIEVEMENT_CHECKS.get(ach.id)
        if check and check(state):
            ach.unlocked_at = today_iso()
            events.append(Event("achievement", f"Достижение: «{ach.title}»"))
            state.add_log("achievement", f"Открыто достижение «{ach.title}»")
    return events


# ---------------------------------------------------------------------------
# Квесты
# ---------------------------------------------------------------------------


def complete_quest(state: GameState, quest_id: str) -> list[Event]:
    quest = state.quest_by_id(quest_id)
    if not quest:
        return [Event("error", "Квест не найден")]
    if not quest.is_available_today():
        return [Event("error", "Этот квест уже выполнен")]

    quest.completed_on.append(today_iso())
    state.stats.quests_done += 1
    points = list(DIFFICULTIES).index(quest.difficulty) + 1
    state.attributes[quest.attribute] = (
        state.attributes.get(quest.attribute, 0) + points
    )

    multiplier = day_multiplier(state)
    xp = _scaled(quest.xp, multiplier)
    coins = _scaled(quest.coins, multiplier)
    events = _add_xp(state, xp, coins)
    events.append(Event("xp", f"+{xp} XP · +{coins} монет{_multiplier_note(multiplier)}"))
    state.add_log("quest", f"Квест «{quest.title}» выполнен")
    events.extend(_check_achievements(state))
    return events


def add_quest(state: GameState, quest: Quest) -> list[Event]:
    state.quests.insert(0, quest)
    state.add_log("info", f"Добавлен квест «{quest.title}»")
    return _check_achievements(state)


def update_quest(
    state: GameState,
    quest_id: str,
    *,
    title: str,
    description: str,
    attribute: str,
    difficulty: str,
    repeat: str,
    icon: str,
) -> list[Event]:
    """Изменить квест, сохранив историю выполнений и созданную дату."""
    quest = state.quest_by_id(quest_id)
    if not quest:
        return [Event("error", "Квест не найден")]
    quest.title = title.strip() or quest.title
    quest.description = description
    quest.attribute = attribute
    quest.difficulty = difficulty
    quest.repeat = repeat
    quest.icon = icon
    state.add_log("info", f"Квест «{quest.title}» изменён")
    return _check_achievements(state)


def delete_quest(state: GameState, quest_id: str) -> None:
    state.quests = [q for q in state.quests if q.id != quest_id]


# ---------------------------------------------------------------------------
# Привычки
# ---------------------------------------------------------------------------


def day_multiplier(state: GameState) -> float:
    """Коэффициент заработка на сегодня от отмеченных привычек.

    Позитивные отметки добавляют бонус, негативные — штраф (по сложности).
    Итог ограничен диапазоном 0.5…2.0.
    """
    total = 1.0
    for habit in state.habits:
        if habit.done_today():
            total += habit.day_effect()
    return round(min(2.0, max(0.5, total)), 2)


def _scaled(value: int, multiplier: float) -> int:
    return max(0, round(value * multiplier))


def _percent(multiplier: float) -> str:
    """Эффект дня в процентах со знаком: +10%, −20%."""
    percent = round((multiplier - 1.0) * 100)
    return f"{'+' if percent >= 0 else '−'}{abs(percent)}%"


def _multiplier_note(multiplier: float) -> str:
    return "" if multiplier == 1.0 else f" · {_percent(multiplier)} за день"


def check_in_habit(state: GameState, habit_id: str) -> list[Event]:
    habit = state.habit_by_id(habit_id)
    if not habit:
        return [Event("error", "Привычка не найдена")]
    if habit.is_negative:
        if habit.done_today():
            return [Event("info", "Срыв уже отмечен сегодня")]
        habit.mark_done()
        state.stats.relapses += 1
        multiplier = day_multiplier(state)
        state.add_log("habit", f"Срыв: «{habit.title}» — заработок сегодня {_percent(multiplier)}")
        events = [Event("info", f"Срыв отмечен. Заработок сегодня {_percent(multiplier)}")]
        events.extend(_check_achievements(state))
        return events
    if not habit.can_check_in():
        return [Event("info", "Сегодня уже отмечено. Возвращайся завтра!")]

    streak = habit.check_in()
    state.stats.habits_done += 1
    state.attributes[habit.attribute] = state.attributes.get(habit.attribute, 0) + 1

    bonus = min(streak, 10) * 2
    multiplier = day_multiplier(state)
    xp = _scaled(habit.base_xp + bonus, multiplier)
    coins = _scaled(max(1, (habit.base_xp + bonus) // 3) + streak // 3, multiplier)

    events = _add_xp(state, xp, coins)
    events.append(Event("xp", f"Серия {streak} дн. · +{xp} XP{_multiplier_note(multiplier)}"))
    state.add_log("habit", f"Привычка «{habit.title}» — серия {streak} дн.")
    events.extend(_check_achievements(state))
    return events


def add_habit(state: GameState, habit: Habit) -> list[Event]:
    state.habits.insert(0, habit)
    state.add_log("info", f"Добавлена привычка «{habit.title}»")
    return _check_achievements(state)


def delete_habit(state: GameState, habit_id: str) -> None:
    state.habits = [h for h in state.habits if h.id != habit_id]


def update_habit(
    state: GameState,
    habit_id: str,
    *,
    title: str,
    attribute: str,
    difficulty: str,
    icon: str,
    kind: str | None = None,
) -> list[Event]:
    habit = state.habit_by_id(habit_id)
    if not habit:
        return [Event("error", "Привычка не найдена")]
    habit.title = title
    habit.attribute = attribute
    habit.difficulty = difficulty
    habit.icon = icon
    if kind:
        habit.kind = kind
    state.add_log("info", f"Привычка «{title}» изменена")
    return _check_achievements(state)


# ---------------------------------------------------------------------------
# Награды
# ---------------------------------------------------------------------------


def buy_reward(state: GameState, reward_id: str, quantity: int = 1) -> list[Event]:
    """Купить награду в количестве quantity: она попадает в инвентарь."""
    reward = state.reward_by_id(reward_id)
    if not reward:
        return [Event("error", "Награда не найдена")]
    quantity = max(1, quantity)
    price = reward.cost * quantity
    if state.player.coins < price:
        missing = price - state.player.coins
        return [Event("error", f"Не хватает {missing} монет")]

    state.player.coins -= price
    reward.purchases += quantity
    reward.owned += quantity
    state.stats.rewards_bought += quantity
    state.stats.biggest_purchase = max(state.stats.biggest_purchase, quantity)
    suffix = f" ×{quantity}" if quantity > 1 else ""
    state.add_log("reward", f"Куплена награда «{reward.title}»{suffix}")

    events = [Event("coins", f"−{price} монет. Заслуженно!")]
    events.extend(_check_achievements(state))
    return events


def use_reward(state: GameState, reward_id: str, quantity: int = 1) -> list[Event]:
    """Использовать награду из инвентаря: её количество уменьшается."""
    reward = state.reward_by_id(reward_id)
    if not reward or reward.owned <= 0:
        return [Event("error", "Награды нет в инвентаре")]
    quantity = min(max(1, quantity), reward.owned)
    reward.owned -= quantity
    state.stats.rewards_used += quantity
    suffix = f" ×{quantity}" if quantity > 1 else ""
    state.add_log("reward", f"Использована награда «{reward.title}»{suffix}")
    events = [Event("info", f"Награда «{reward.title}» использована")]
    events.extend(_check_achievements(state))
    return events


def inventory(state: GameState) -> list[Reward]:
    """Награды, которые куплены и ещё не использованы."""
    return [reward for reward in state.rewards if reward.owned > 0]


def add_reward(state: GameState, reward: Reward) -> None:
    state.rewards.append(reward)
    state.add_log("info", f"Добавлена награда «{reward.title}»")


def update_reward(
    state: GameState,
    reward_id: str,
    *,
    title: str,
    cost: int,
    icon: str | None = None,
) -> None:
    """Изменить название, стоимость и значок награды, сохранив историю покупок."""
    reward = state.reward_by_id(reward_id)
    if not reward:
        return
    reward.title = title.strip() or reward.title
    reward.cost = max(1, cost)
    if icon:
        reward.icon = icon
    state.add_log("info", f"Награда «{reward.title}» изменена")


def delete_reward(state: GameState, reward_id: str) -> None:
    state.rewards = [reward for reward in state.rewards if reward.id != reward_id]


# ---------------------------------------------------------------------------
# Сводки для интерфейса
# ---------------------------------------------------------------------------


def today_quests(state: GameState) -> list[Quest]:
    """Квесты, актуальные сегодня.

    Ежедневные и еженедельные остаются в списке всегда (они сбрасываются),
    разовый — только пока не выполнен: закрытое разовое дело уходит из плана.
    """
    return [
        q
        for q in state.quests
        if not q.archived
        and (q.repeat in ("daily", "weekly") or not q.completed_on)
    ]


def today_progress(state: GameState) -> tuple[int, int]:
    quests = today_quests(state)
    done = sum(1 for q in quests if not q.is_available_today())
    return done, len(quests)


def total_streak(state: GameState) -> int:
    return sum(h.streak for h in state.habits)


def attribute_level(value: int) -> int:
    return value // 5 + 1


def attribute_progress(value: int) -> float:
    return (value % 5) / 5


def xp_progress(state: GameState) -> float:
    return state.player.xp_in_level / max(1, state.player.xp_to_next_level)


# ---------------------------------------------------------------------------
# Визуализация серии: щит героя и огонёк
# ---------------------------------------------------------------------------

#: Серия, при которой щит героя становится полностью видимым.
SHIELD_FULL_DAYS = 30
#: Первый месяц после заполнения щита: огонёк растёт.
FLAME_GROWTH_DAYS = 30
#: Дальше каждый месяц огонёк плавно переходит к новому цвету.
FLAME_COLOR_MONTH_DAYS = 30
#: Серия, при которой огонёк достигает максимального размера.
FLAME_FULL_DAYS = SHIELD_FULL_DAYS + FLAME_GROWTH_DAYS

#: Цвета огонька по месяцам после роста; после года цикл повторяется.
FLAME_COLORS = (
    "#FF9F5A",  # оранжевый
    "#FFC466",  # золотой
    "#FFF176",  # жёлтый
    "#A3E635",  # лаймовый
    "#3DE1B0",  # мятный
    "#4CC9F0",  # голубой
    "#5C9DFF",  # синий
    "#7C5CFF",  # фиолетовый
    "#B388FF",  # лавандовый
    "#FF6B9D",  # розовый
    "#FF4D6D",  # алый
    "#FF8A65",  # коралловый
)


def shield_opacity(streak: int) -> float:
    """Яркость щита: 0.25 без серии, 1.0 к 30 дням."""
    progress = min(max(streak, 0), SHIELD_FULL_DAYS) / SHIELD_FULL_DAYS
    return 0.25 + 0.75 * progress


def flame_progress(streak: int) -> float:
    """Размер огонька: 0 до 30 дней, 1.0 через месяц после заполнения щита."""
    if streak <= SHIELD_FULL_DAYS:
        return 0.0
    return min(
        (streak - SHIELD_FULL_DAYS) / FLAME_GROWTH_DAYS,
        1.0,
    )


def _mix_hex(start: str, end: str, t: float) -> str:
    """Линейно смешать два HEX-цвета (t от 0 до 1)."""
    start_rgb = [int(start[i : i + 2], 16) for i in (1, 3, 5)]
    end_rgb = [int(end[i : i + 2], 16) for i in (1, 3, 5)]
    mixed = [
        round(a + (b - a) * t)
        for a, b in zip(start_rgb, end_rgb)
    ]
    return "#" + "".join(f"{channel:02X}" for channel in mixed)


def flame_color(streak: int) -> str:
    """Цвет огонька: растёт оранжевым, затем каждый месяц плавно меняется."""
    if streak < FLAME_FULL_DAYS:
        return FLAME_COLORS[0]

    months = (streak - FLAME_FULL_DAYS) // FLAME_COLOR_MONTH_DAYS
    month_progress = (
        (streak - FLAME_FULL_DAYS) % FLAME_COLOR_MONTH_DAYS
    ) / FLAME_COLOR_MONTH_DAYS
    current = FLAME_COLORS[months % len(FLAME_COLORS)]
    following = FLAME_COLORS[(months + 1) % len(FLAME_COLORS)]
    return _mix_hex(current, following, month_progress)


def level_floor(level: int) -> int:
    """Сколько XP суммарно нужно для текущего уровня."""
    return xp_for_level(level)


def next_attribute_name(code: str) -> str:
    return ATTRIBUTES.get(code, (code, code))[0]


def today_label() -> str:
    months = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]
    d = date.today()
    weekdays = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]
    return f"{weekdays[d.weekday()]}, {d.day} {months[d.month - 1]}"
