"""Слой доступа к данным: Supabase через supabase-py.

Это единственное место в проекте, которое знает про базу. UI (main.py)
работает только с Task и TaskRepo, поэтому замена источника данных
не потребует переписывать экраны.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from supabase import Client, create_client

TABLE = "tasks"

# Подсказки для типовых ошибок Supabase: текст исключения -> что это значит.
# Ровно те три гипотезы, которые разбираются в README (RLS, ключ, имя таблицы).
_HINTS: tuple[tuple[str, str], ...] = (
    (
        "row-level security",
        "Сработала RLS: у таблицы tasks нет политики на эту операцию.\n"
        "Откройте Supabase → Authentication → Policies и выполните db/schema.sql.",
    ),
    (
        "invalid api key",
        "Неверный SUPABASE_ANON_KEY в src/config.py.\n"
        "Возьмите anon public key из Supabase → Project Settings → API.",
    ),
    (
        "invalid url",
        "Неверный SUPABASE_URL в src/config.py (нужен вид https://<ref>.supabase.co).",
    ),
    (
        "does not exist",
        "Таблица tasks не найдена: выполните db/schema.sql в SQL Editor.",
    ),
    (
        "name or service not known",
        "Хост из SUPABASE_URL не резолвится: проверьте URL и интернет.",
    ),
)


class RepoError(Exception):
    """Ошибка с текстом, который можно показать пользователю как есть."""


@dataclass(frozen=True)
class Task:
    """Запись таблицы tasks в том виде, в котором её ждёт UI."""

    id: str
    title: str
    done: bool
    created_at: str


def _explain(exc: Exception) -> str:
    """Превращает техническое исключение в понятное сообщение."""
    raw = f"{type(exc).__name__}: {exc}"
    lowered = raw.lower()
    for needle, hint in _HINTS:
        if needle in lowered:
            return f"{hint}\n\nТехнический текст: {raw}"
    return f"Запрос к Supabase не удался.\n\nТехнический текст: {raw}"


# Имена, под которыми ключ может лежать в config.py: сначала привычный
# SUPABASE_ANON_KEY, затем новые publishable-ключи Supabase (sb_publishable_...).
_KEY_NAMES = ("SUPABASE_ANON_KEY", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_KEY")


def _credentials() -> tuple[str, str]:
    """Читает URL и публичный ключ из config.py, при его отсутствии — из окружения."""
    try:
        import config as _config  # type: ignore[import-not-found]
    except ImportError:
        _config = None

    def value(name: str) -> str:
        if _config is not None:
            return str(getattr(_config, name, "") or "")
        return os.environ.get(name, "")

    url = value("SUPABASE_URL")
    key = next((found for found in (value(name) for name in _KEY_NAMES) if found), "")

    if not url or not key or "<" in url:
        raise RepoError(
            "Не заполнены SUPABASE_URL и ключ проекта.\n\n"
            "Скопируйте src/config.example.py в src/config.py и вставьте значения "
            "из Supabase: кнопка Connect в шапке проекта либо Settings → API Keys."
        )
    return url, key


class TaskRepo:
    """CRUD-операции над таблицей tasks."""

    def __init__(self) -> None:
        url, key = _credentials()
        self._client: Client = create_client(url, key)

    # --- чтение ---------------------------------------------------------

    def list_tasks(self) -> list[Task]:
        """Все задачи, сначала новые."""
        rows = self._call(
            lambda: self._client.table(TABLE)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [
            Task(
                id=str(row["id"]),
                title=str(row.get("title") or ""),
                done=bool(row.get("done")),
                created_at=str(row.get("created_at") or ""),
            )
            for row in rows
        ]

    # --- изменение ------------------------------------------------------

    def add_task(self, title: str) -> None:
        clean = title.strip()
        if not clean:
            raise RepoError("Нельзя добавить пустую задачу.")
        self._call(
            lambda: self._client.table(TABLE)
            .insert({"title": clean, "done": False})
            .execute()
        )

    def set_done(self, task_id: str, done: bool) -> None:
        self._call(
            lambda: self._client.table(TABLE)
            .update({"done": done})
            .eq("id", task_id)
            .execute()
        )

    def delete_task(self, task_id: str) -> None:
        self._call(
            lambda: self._client.table(TABLE).delete().eq("id", task_id).execute()
        )

    # --- общее ----------------------------------------------------------

    @staticmethod
    def _call(operation):
        """Выполняет запрос и переводит любую ошибку в RepoError."""
        try:
            response = operation()
        except RepoError:
            raise
        except Exception as exc:  # сеть, postgrest.APIError, AuthApiError и т.п.
            raise RepoError(_explain(exc)) from exc
        return getattr(response, "data", None) or []
