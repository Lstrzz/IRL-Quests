"""Сохранение состояния игры в JSON.

На Android Flet задаёт переменную окружения FLET_APP_STORAGE_DATA — это
каталог, доступный приложению для записи. Локально используется
~/.irl_quests. Запись атомарная: сначала во временный файл, затем replace,
плюс резервная копия предыдущего состояния.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import fields
from pathlib import Path
from typing import Any, TypeVar

from .models import (
    Achievement,
    GameState,
    Habit,
    Player,
    Quest,
    Reward,
    Stats,
    default_state,
)

T = TypeVar("T")

APP_DIR_NAME = "irl_quests"
DATA_FILE = "save.json"
MAX_SAVE_SIZE = 5 * 1024 * 1024


def data_dir() -> Path:
    """Каталог для данных приложения."""
    override = os.getenv("IRL_QUESTS_DATA_DIR")
    if override:
        return Path(override)
    flet_dir = os.getenv("FLET_APP_STORAGE_DATA")
    if flet_dir:
        return Path(flet_dir)
    return Path.home() / f".{APP_DIR_NAME}"


def _filtered(cls: type[T], data: dict[str, Any]) -> dict[str, Any]:
    """Оставить только известные поля класса (защита от старых сохранений)."""
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in names}


def state_to_dict(state: GameState) -> dict[str, Any]:
    return {
        "version": state.version,
        "player": {
            "name": state.player.name,
            "xp": state.player.xp,
            "coins": state.player.coins,
            "created_at": state.player.created_at,
        },
        "stats": {
            "quests_done": state.stats.quests_done,
            "habits_done": state.stats.habits_done,
            "xp_earned": state.stats.xp_earned,
            "coins_earned": state.stats.coins_earned,
            "rewards_bought": state.stats.rewards_bought,
            "rewards_used": state.stats.rewards_used,
            "biggest_purchase": state.stats.biggest_purchase,
            "relapses": state.stats.relapses,
        },
        "attributes": dict(state.attributes),
        "quests": [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "attribute": q.attribute,
                "difficulty": q.difficulty,
                "repeat": q.repeat,
                "icon": q.icon,
                "created_at": q.created_at,
                "completed_on": list(q.completed_on),
                "archived": q.archived,
            }
            for q in state.quests
        ],
        "habits": [
            {
                "id": h.id,
                "title": h.title,
                "icon": h.icon,
                "attribute": h.attribute,
                "difficulty": h.difficulty,
                "kind": h.kind,
                "streak": h.streak,
                "best_streak": h.best_streak,
                "last_done": h.last_done,
                "history": list(h.history),
            }
            for h in state.habits
        ],
        "rewards": [
            {
                "id": r.id,
                "title": r.title,
                "cost": r.cost,
                "icon": r.icon,
                "purchases": r.purchases,
                "owned": r.owned,
            }
            for r in state.rewards
        ],
        "achievements": [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "icon": a.icon,
                "unlocked_at": a.unlocked_at,
            }
            for a in state.achievements
        ],
        "log": list(state.log),
    }


def state_from_dict(data: dict[str, Any]) -> GameState:
    """Собрать состояние из словаря, устойчиво к отсутствующим полям."""
    state = GameState(version=int(data.get("version", 1)))

    if isinstance(data.get("player"), dict):
        state.player = Player(**_filtered(Player, data["player"]))
    if isinstance(data.get("stats"), dict):
        state.stats = Stats(**_filtered(Stats, data["stats"]))

    attributes = data.get("attributes")
    if isinstance(attributes, dict):
        for code in state.attributes:
            state.attributes[code] = int(attributes.get(code, 0))

    for raw in data.get("quests", []) or []:
        if isinstance(raw, dict):
            quest = Quest(**_filtered(Quest, raw))
            quest.completed_on = list(quest.completed_on or [])
            state.quests.append(quest)

    for raw in data.get("habits", []) or []:
        if isinstance(raw, dict):
            habit = Habit(**_filtered(Habit, raw))
            habit.history = list(habit.history or [])
            state.habits.append(habit)

    for raw in data.get("rewards", []) or []:
        if isinstance(raw, dict):
            state.rewards.append(Reward(**_filtered(Reward, raw)))

    for raw in data.get("achievements", []) or []:
        if isinstance(raw, dict):
            state.achievements.append(Achievement(**_filtered(Achievement, raw)))

    if isinstance(data.get("log"), list):
        state.log = [entry for entry in data["log"] if isinstance(entry, dict)][:60]

    # Достижения из новых версий приложения добавляем, не теряя прогресс.
    # Тексты и иконки известных достижений обновляем под текущую версию,
    # а сохранённую дату открытия оставляем.
    existing = {ach.id: ach for ach in state.achievements}
    ordered: list[Achievement] = []
    for default in default_state().achievements:
        current = existing.get(default.id)
        if current is None:
            ordered.append(default)
            continue
        current.title = default.title
        current.description = default.description
        current.icon = default.icon
        ordered.append(current)

    known = {ach.id for ach in ordered}
    ordered.extend(ach for ach in state.achievements if ach.id not in known)
    state.achievements = ordered

    # Нормализация значений.
    state.player.xp = max(0, state.player.xp)
    state.player.coins = max(0, state.player.coins)
    state.stats.quests_done = max(0, state.stats.quests_done)
    state.stats.habits_done = max(0, state.stats.habits_done)
    state.stats.rewards_bought = max(0, state.stats.rewards_bought)

    return state


def save_bytes(state: GameState) -> bytes:
    """Сериализовать состояние в JSON-байты для экспорта."""
    payload = json.dumps(state_to_dict(state), ensure_ascii=False, indent=2)
    return payload.encode("utf-8")


def state_from_bytes(raw: bytes) -> GameState:
    """Разобрать файл сохранения, выбранный пользователем.

    Отличие от :func:`state_from_dict`: проверяет, что это вообще файл
    сохранения IRL Quests, и не даёт загрузить произвольный или слишком
    большой JSON. Ошибка формата — ``ValueError`` с текстом для снекбара.
    """
    if not raw:
        raise ValueError("файл пуст")
    if len(raw) > MAX_SAVE_SIZE:
        raise ValueError("файл больше 5 МБ")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("файл не является корректным JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("player"), dict):
        raise ValueError("это не файл сохранения IRL Quests")
    try:
        return state_from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("файл сохранения повреждён") from exc


class Storage:
    """Простое JSON-хранилище с атомарной записью."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or data_dir()
        self.path = self.directory / DATA_FILE

    def load(self) -> GameState:
        if not self.path.exists():
            state = default_state()
            self.save(state)
            return state
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                raise ValueError("Корень файла сохранения — не объект")
            return state_from_dict(data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            # Битое сохранение не должно блокировать запуск приложения.
            backup = self.path.with_suffix(".broken.json")
            try:
                shutil.copy2(self.path, backup)
            except OSError:
                pass
            state = default_state()
            self.save(state)
            return state

    def save(self, state: GameState) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = save_bytes(state).decode("utf-8")
        fd, tmp_name = tempfile.mkstemp(
            dir=self.directory, prefix=".save-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            if self.path.exists():
                try:
                    shutil.copy2(self.path, self.path.with_suffix(".bak.json"))
                except OSError:
                    pass
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def reset(self) -> GameState:
        self.directory.mkdir(parents=True, exist_ok=True)
        state = default_state()
        self.save(state)
        return state
