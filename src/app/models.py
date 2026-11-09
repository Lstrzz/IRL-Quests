"""Модели данных приложения «IRL Quests».

Здесь нет ни одной зависимости от Flet: чистый Python, который легко
тестировать и при желании переиспользовать в другом интерфейсе.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


# ---------------------------------------------------------------------------
# Справочники
# ---------------------------------------------------------------------------

#: Атрибуты героя: код -> (название, короткое название)
ATTRIBUTES: dict[str, tuple[str, str]] = {
    "strength": ("Сила", "СИЛ"),
    "intellect": ("Интеллект", "ИНТ"),
    "will": ("Воля", "ВОЛ"),
    "charisma": ("Харизма", "ХАР"),
}

#: Сложность квеста: код -> (название, XP)
DIFFICULTIES: dict[str, tuple[str, int]] = {
    "easy": ("Легко", 15),
    "normal": ("Обычно", 30),
    "hard": ("Сложно", 60),
    "epic": ("Эпично", 120),
}

#: Тип повтора квеста: код -> название
REPEATS: dict[str, str] = {
    "daily": "Ежедневный",
    "weekly": "Еженедельный",
    "once": "Разовый",
}

#: Тип привычки: код -> название
HABIT_KINDS: dict[str, str] = {
    "positive": "Позитивная",
    "negative": "Негативная",
}

#: Влияние отметки на заработок дня (доля): позитивная даёт бонус,
#: негативная — штраф. Зависит от сложности.
HABIT_DAY_EFFECT: dict[str, float] = {
    "easy": 0.05,
    "normal": 0.10,
    "hard": 0.20,
    "epic": 0.30,
}

#: Сложность привычки: код -> (название, базовый XP за отметку)
HABIT_DIFFICULTIES: dict[str, tuple[str, int]] = {
    "easy": ("Легко", 10),
    "normal": ("Обычно", 15),
    "hard": ("Сложно", 25),
    "epic": ("Эпично", 40),
}

LEVEL_BASE_XP = 100  # XP для перехода со 1-го на 2-й уровень


def today_iso() -> str:
    return date.today().isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Сущности
# ---------------------------------------------------------------------------


def coins_for_xp(xp: int) -> int:
    """Монеты за квест: половина опыта, но не меньше одной."""
    return max(1, xp // 2)


@dataclass
class Quest:
    """Задача, за выполнение которой герой получает опыт и монеты."""

    title: str
    description: str = ""
    attribute: str = "will"
    difficulty: str = "normal"
    repeat: str = "daily"
    icon: str = "flag"
    created_at: str = field(default_factory=today_iso)
    completed_on: list[str] = field(default_factory=list)
    archived: bool = False
    id: str = field(default_factory=lambda: new_id("q"))

    # -- вычисляемые свойства ------------------------------------------------
    @property
    def xp(self) -> int:
        return DIFFICULTIES.get(self.difficulty, DIFFICULTIES["normal"])[1]

    @property
    def coins(self) -> int:
        return coins_for_xp(self.xp)

    def is_done_today(self) -> bool:
        return today_iso() in self.completed_on

    def is_available_today(self) -> bool:
        """Доступен ли квест сегодня (с учётом периодичности)."""
        if self.archived:
            return False
        today = date.today()
        if self.repeat == "once":
            return not self.completed_on
        if self.repeat == "weekly":
            week_start = today - timedelta(days=today.weekday())
            return not any(
                date.fromisoformat(d) >= week_start for d in self.completed_on
            )
        return not self.is_done_today()


@dataclass
class Habit:
    """Привычка с серией последовательных отметок."""

    title: str
    icon: str = "repeat"
    attribute: str = "will"
    difficulty: str = "normal"
    kind: str = "positive"
    streak: int = 0
    best_streak: int = 0
    last_done: str | None = None
    history: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("h"))

    @property
    def difficulty_name(self) -> str:
        return HABIT_DIFFICULTIES.get(
            self.difficulty, HABIT_DIFFICULTIES["normal"]
        )[0]

    @property
    def base_xp(self) -> int:
        return HABIT_DIFFICULTIES.get(
            self.difficulty, HABIT_DIFFICULTIES["normal"]
        )[1]

    @property
    def is_negative(self) -> bool:
        return self.kind == "negative"

    def day_effect(self) -> float:
        """Вклад отметки в коэффициент заработка дня: +бонус или −штраф."""
        value = HABIT_DAY_EFFECT.get(self.difficulty, HABIT_DAY_EFFECT["normal"])
        return -value if self.is_negative else value

    def mark_done(self) -> None:
        """Отметить без серии: для вредных привычек."""
        today = today_iso()
        self.last_done = today
        if today not in self.history:
            self.history.append(today)

    def done_today(self) -> bool:
        return self.last_done == today_iso()

    def can_check_in(self) -> bool:
        return not self.done_today()

    def check_in(self) -> int:
        """Отметить привычку. Возвращает количество дней серии после отметки."""
        if self.done_today():
            return self.streak

        today = date.today()
        yesterday = (today - timedelta(days=1)).isoformat()
        if self.last_done == yesterday:
            self.streak += 1
        else:
            self.streak = 1

        self.last_done = today.isoformat()
        self.best_streak = max(self.best_streak, self.streak)
        if today.isoformat() not in self.history:
            self.history.append(today.isoformat())
        return self.streak

    def days_since_last(self) -> int | None:
        if not self.last_done:
            return None
        return (date.today() - date.fromisoformat(self.last_done)).days

    def is_broken(self) -> bool:
        """Серия потеряна, если отметка была раньше вчера."""
        if not self.last_done or self.streak == 0:
            return False
        return date.fromisoformat(self.last_done) < date.today() - timedelta(days=1)


@dataclass
class Reward:
    """Награда, которую можно купить за монеты."""

    title: str
    cost: int = 100
    icon: str = "redeem"
    purchases: int = 0
    owned: int = 0
    id: str = field(default_factory=lambda: new_id("r"))


@dataclass
class Achievement:
    """Достижение. Условие проверяется движком (см. engine.ACHIEVEMENTS)."""

    id: str
    title: str
    description: str
    icon: str
    unlocked_at: str | None = None


@dataclass
class Player:
    name: str = "Странник"
    xp: int = 0
    coins: int = 75
    created_at: str = field(default_factory=today_iso)

    @property
    def level(self) -> int:
        level = 1
        while self.xp >= xp_for_level(level + 1):
            level += 1
        return level

    @property
    def xp_in_level(self) -> int:
        return self.xp - xp_for_level(self.level)

    @property
    def xp_to_next_level(self) -> int:
        return xp_for_level(self.level + 1) - xp_for_level(self.level)


@dataclass
class Stats:
    quests_done: int = 0
    habits_done: int = 0
    xp_earned: int = 0
    coins_earned: int = 0
    rewards_bought: int = 0
    rewards_used: int = 0
    biggest_purchase: int = 0
    relapses: int = 0


@dataclass
class GameState:
    """Полное состояние игры — то, что сохраняется в JSON."""

    version: int = 1
    player: Player = field(default_factory=Player)
    stats: Stats = field(default_factory=Stats)
    attributes: dict[str, int] = field(
        default_factory=lambda: {code: 0 for code in ATTRIBUTES}
    )
    quests: list[Quest] = field(default_factory=list)
    habits: list[Habit] = field(default_factory=list)
    rewards: list[Reward] = field(default_factory=list)
    achievements: list[Achievement] = field(default_factory=list)
    log: list[dict] = field(default_factory=list)

    # -- удобные выборки -----------------------------------------------------
    def quest_by_id(self, quest_id: str) -> Quest | None:
        return next((q for q in self.quests if q.id == quest_id), None)

    def habit_by_id(self, habit_id: str) -> Habit | None:
        return next((h for h in self.habits if h.id == habit_id), None)

    def reward_by_id(self, reward_id: str) -> Reward | None:
        return next((r for r in self.rewards if r.id == reward_id), None)

    def achievement_by_id(self, ach_id: str) -> Achievement | None:
        return next((a for a in self.achievements if a.id == ach_id), None)

    def add_log(self, kind: str, text: str) -> None:
        self.log.insert(
            0,
            {"kind": kind, "text": text, "at": datetime.now().isoformat(timespec="minutes")},
        )
        del self.log[60:]


# ---------------------------------------------------------------------------
# Кривая опыта
# ---------------------------------------------------------------------------


def xp_for_level(level: int) -> int:
    """Суммарный XP, необходимый для достижения уровня.

    Уровень 1 — 0 XP, 2 — 100, 3 — 300, 4 — 600, 5 — 1000 ...
    """
    if level <= 1:
        return 0
    n = level - 1
    return LEVEL_BASE_XP * n * (n + 1) // 2


_LEVEL_TITLES = (
    "Новичок",
    "Ученик",
    "Искатель",
    "Практик",
    "Адепт",
    "Ветеран",
    "Мастер",
    "Герой",
    "Хранитель",
    "Легенда",
)

_ROMAN = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def _roman(number: int) -> str:
    if number <= 0 or number >= 4000:
        return str(number)
    parts: list[str] = []
    for value, symbol in _ROMAN:
        count, number = divmod(number, value)
        if count:
            parts.append(symbol * count)
    return "".join(parts)


def level_title(level: int) -> str:
    """Звание героя: каждое держится 10 уровней.

    1–10 — Новичок, 11–20 — Ученик, …, 71–80 — Герой, 81–90 — Хранитель,
    91–100 — Легенда. Дальше надпись продолжает меняться каждые 10 уровней:
    101–110 — «Легенда II», 111–120 — «Легенда III» и так далее.
    """
    level = max(level, 1)
    decade = (level - 1) // 10
    if decade < len(_LEVEL_TITLES):
        return _LEVEL_TITLES[decade]
    return f"Легенда {_roman(decade - len(_LEVEL_TITLES) + 2)}"


def default_state() -> GameState:
    """Стартовый набор квестов, привычек и наград."""
    state = GameState()
    state.quests = [
        Quest(
            title="Зарядка 15 минут",
            description="Любая активность: разминка, растяжка или короткая тренировка.",
            attribute="strength",
            difficulty="normal",
            repeat="daily",
            icon="fitness_center",
        ),
        Quest(
            title="Прочитать 10 страниц",
            description="Художественная или нон-фикшн — не важно. Главное — вперёд.",
            attribute="intellect",
            difficulty="easy",
            repeat="daily",
            icon="menu_book",
        ),
        Quest(
            title="Прогулка 30 минут",
            description="Без телефона в руке. Наблюдай за миром вокруг.",
            attribute="will",
            difficulty="easy",
            repeat="daily",
            icon="directions_walk",
        ),
        Quest(
            title="Лечь спать до 23:00",
            description="Сон — базовый бафф ко всем характеристикам.",
            attribute="will",
            difficulty="normal",
            repeat="daily",
            icon="bedtime",
        ),
        Quest(
            title="Разобрать одну полку",
            description="Маленький шаг к порядку в доме и в голове.",
            attribute="will",
            difficulty="hard",
            repeat="once",
            icon="inventory_2",
        ),
    ]
    state.habits = [
        Habit(
            title="Стакан воды утром",
            icon="water_drop",
            attribute="strength",
            difficulty="easy",
        ),
        Habit(
            title="Дневник вечером",
            icon="edit_note",
            attribute="intellect",
            difficulty="normal",
        ),
        Habit(
            title="Без соцсетей до обеда",
            icon="phone_disabled",
            attribute="will",
            difficulty="hard",
        ),
    ]
    state.rewards = [
        Reward(title="30 минут сериала", cost=60, icon="tv"),
        Reward(title="Час видеоигр", cost=120, icon="sports_esports"),
        Reward(title="Вкусный десерт", cost=150, icon="cake"),
        Reward(title="День без задач", cost=400, icon="beach_access"),
    ]
    state.achievements = [
        # Квесты
        Achievement("first_step", "Первый шаг", "Выполни первый квест", "rocket_launch"),
        Achievement("quests_10", "Трудяга", "Выполни 10 квестов", "task_alt"),
        Achievement("quests_25", "В потоке", "Выполни 25 квестов", "check_circle"),
        Achievement("quests_50", "Машина прогресса", "Выполни 50 квестов", "bolt"),
        Achievement("quests_100", "Сотник", "Выполни 100 квестов", "flag"),
        Achievement("quests_250", "Неудержимый", "Выполни 250 квестов", "speed"),
        Achievement("quests_500", "Легенда дел", "Выполни 500 квестов", "emoji_events"),
        # Привычки
        Achievement("habits_1", "Первый раз", "Отметь первую привычку", "done_all"),
        Achievement("habits_10", "Привычка", "10 отметок привычек", "edit_note"),
        Achievement("habits_50", "Ритуал", "50 отметок привычек", "local_activity"),
        Achievement("habits_100", "Второй характер", "100 отметок привычек", "calendar_month"),
        Achievement("habits_250", "Автоматизм", "250 отметок привычек", "auto_awesome"),
        # Серии
        Achievement("streak_3", "В ритме", "3 дня подряд в привычке", "local_fire_department"),
        Achievement("streak_7", "Несгибаемый", "7 дней подряд в привычке", "whatshot"),
        Achievement("streak_14", "Две недели", "14 дней подряд в привычке", "date_range"),
        Achievement("streak_30", "Месяц силы", "30 дней подряд в привычке", "event_available"),
        Achievement("streak_60", "Два месяца", "60 дней подряд в привычке", "timeline"),
        Achievement("streak_100", "Сто дней", "100 дней подряд в привычке", "stars"),
        Achievement("streak_365", "Год дисциплины", "365 дней подряд в привычке", "celebration"),
        # Уровни и звания
        Achievement("level_3", "В пути", "Достигни 3 уровня", "trending_up"),
        Achievement("level_5", "Опытный", "Достигни 5 уровня", "military_tech"),
        Achievement("level_10", "Десятка", "Достигни 10 уровня", "grade"),
        Achievement("level_21", "Искатель", "Достигни 21 уровня", "travel_explore"),
        Achievement("level_41", "Адепт", "Достигни 41 уровня", "workspace_premium"),
        Achievement("level_61", "Мастер", "Достигни 61 уровня", "psychology"),
        Achievement("level_71", "Герой", "Достигни 71 уровня", "shield"),
        Achievement("level_81", "Хранитель", "Достигни 81 уровня", "verified"),
        Achievement("level_91", "Легенда", "Достигни 91 уровня", "diamond"),
        Achievement("level_101", "Легенда II", "Достигни 101 уровня", "star"),
        # Характеристики
        Achievement("balanced", "Гармония", "Прокачай каждый атрибут до 5", "self_improvement"),
        Achievement("attr_any_10", "Сильная сторона", "Прокачай атрибут до 10", "fitness_center"),
        Achievement("attr_any_25", "Специалист", "Прокачай атрибут до 25", "menu_book"),
        Achievement("attr_any_50", "Эксперт", "Прокачай атрибут до 50", "insights"),
        Achievement("attr_all_10", "Разносторонний", "Все атрибуты до 10", "radar"),
        Achievement("attr_all_25", "Универсал", "Все атрибуты до 25", "stars"),
        # Опыт
        Achievement("xp_1000", "Тысяча", "Заработай 1 000 XP", "bolt"),
        Achievement("xp_10000", "Десять тысяч", "Заработай 10 000 XP", "trending_up"),
        Achievement("xp_100000", "Сто тысяч", "Заработай 100 000 XP", "auto_awesome"),
        Achievement("xp_500000", "Полмиллиона", "Заработай 500 000 XP", "workspace_premium"),
        # Награды
        Achievement("rewards_1", "Первая награда", "Купи первую награду", "redeem"),
        Achievement("collector", "Коллекционер", "Купи 3 награды", "shopping_bag"),
        Achievement("rewards_10", "Знаток наград", "Купи 10 наград", "celebration"),
        Achievement("rewards_25", "Мастер отдыха", "Купи 25 наград", "beach_access"),
        Achievement("bulk_buy", "Оптовик", "Купи сразу 5 наград за одну покупку", "shopping_cart"),
        Achievement("inventory_5", "Запасливый", "Держи в инвентаре 5 наград одновременно", "inventory_2"),
        Achievement("rewards_used_1", "Заслуженный отдых", "Используй первую награду", "savings"),
        Achievement("rewards_used_10", "Ценитель отдыха", "Используй 10 наград", "card_giftcard"),
        Achievement("rewards_used_25", "Мастер заслуженного отдыха", "Используй 25 наград", "workspace_premium"),
        Achievement("rewards_50", "Щедрый покупатель", "Купи 50 наград", "castle"),
        Achievement("rewards_100", "Владыка наград", "Купи 100 наград", "emoji_events"),
        Achievement("rewards_used_50", "Вкус жизни", "Используй 50 наград", "toys"),
        Achievement("rewards_used_100", "Король отдыха", "Используй 100 наград", "castle"),
        Achievement("inventory_10", "Склад удовольствий", "Держи в инвентаре 10 наград одновременно", "pool"),
        Achievement("inventory_20", "Кладовая", "Держи в инвентаре 20 наград одновременно", "diamond"),
        Achievement("bulk_10", "Оптом и с выгодой", "Купи сразу 10 наград за одну покупку", "local_pizza"),
        # Планирование
        Achievement("planner_10", "Планировщик", "10 квестов в списке", "playlist_add"),
        Achievement("planner_25", "Архитектор", "25 квестов в списке", "checklist"),
        Achievement("habit_maker_5", "Наставник", "5 привычек в списке", "add_task"),
        Achievement("habit_maker_10", "Садовник", "10 привычек в списке", "menu_book"),
        Achievement("negative_3", "Осознанность", "Добавь 3 негативные привычки", "warning_amber"),
        Achievement("relapse_1", "Честность", "Честно отметь первый срыв", "visibility"),
        Achievement("relapse_10", "Самокритичность", "Отметь 10 срывов", "rule"),
        Achievement("clean_7", "Неделя без срыва", "7 дней без срыва после последнего", "spa"),
        Achievement("clean_30", "Месяц без срыва", "30 дней без срыва после последнего", "nightlight"),
        Achievement("clean_365", "Год без срыва", "365 дней без срыва после последнего", "verified"),
    ]
    state.add_log("start", "Приключение началось. Добро пожаловать!")
    return state
