"""Проверка UI без сети: подменяет TaskRepo заглушкой.

Запуск (нужен установленный flet):
    python tests/smoke_ui.py

Скрипт строит настоящий экран из src/main.py и «нажимает» кнопки, подставив
вместо Supabase фейковый репозиторий. Ловит опечатки в API Flet (имена
контролов, атрибутов, обработчиков) за секунды — до того, как вы потратите
десять минут на облачную сборку.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import main as app  # noqa: E402  (импорт после правки sys.path)
from repo import RepoError, Task  # noqa: E402


class FakeRepo:
    """Тот же интерфейс, что у TaskRepo, но данные живут в памяти."""

    def __init__(self) -> None:
        self.rows: list[Task] = [
            Task(id="1", title="Купить молоко", done=False, created_at="2026-01-01"),
            Task(id="2", title="Сдать ПК-2", done=True, created_at="2026-01-02"),
        ]
        self.deleted: list[str] = []

    def list_tasks(self) -> list[Task]:
        return list(self.rows)

    def add_task(self, title: str) -> None:
        self.rows.insert(
            0,
            Task(id=f"new-{len(self.rows)}", title=title, done=False, created_at=""),
        )

    def set_done(self, task_id: str, done: bool) -> None:
        self.rows = [
            Task(
                id=t.id,
                title=t.title,
                done=done if t.id == task_id else t.done,
                created_at=t.created_at,
            )
            for t in self.rows
        ]

    def delete_task(self, task_id: str) -> None:
        self.deleted.append(task_id)
        self.rows = [t for t in self.rows if t.id != task_id]


class FakePage:
    """Минимальная замена ft.Page: только то, что реально трогает main.py."""

    def __init__(self) -> None:
        self.title = ""
        self.padding = 0
        self.controls: list = []
        self.updates = 0

    def add(self, *controls) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.updates += 1


def texts_of(control) -> list[str]:
    """Рекурсивно собирает строковые значения контролов."""
    found: list[str] = []
    value = getattr(control, "value", None)
    if isinstance(value, str) and value:
        found.append(value)
    for child in getattr(control, "controls", None) or []:
        found.extend(texts_of(child))
    return found


def check() -> None:
    fake = FakeRepo()
    app.TaskRepo = lambda: fake  # type: ignore[assignment]

    page = FakePage()
    app.main(page)

    # Раскладка экрана: 0 заголовок, 1 поле+кнопка, 2 строка ошибки,
    # 3 разделитель, 4 список, 5 счётчик.
    assert len(page.controls) == 6, f"ожидалось 6 блоков, получено {len(page.controls)}"
    assert "Список задач" in texts_of(page.controls[0]), "нет заголовка"

    field = page.controls[1].controls[0]
    add_button = page.controls[1].controls[1]
    status = page.controls[2]
    tasks_list = page.controls[4]
    counter = page.controls[5]

    assert len(tasks_list.controls) == 2, "список не отрисован из репозитория"
    assert "Всего: 2" in counter.value, f"неверный счётчик: {counter.value}"

    # 1. Добавление по Enter в поле ввода.
    field.value = "Новая задача"
    field.on_submit(None)
    assert any(t.title == "Новая задача" for t in fake.rows), "on_submit не добавил задачу"
    assert field.value == "", "поле не очистилось после добавления"

    # 2. Пустой ввод не должен уходить в базу.
    rows_before = len(fake.rows)
    field.value = "   "
    add_button.on_click(None)
    assert len(fake.rows) == rows_before, "пустая задача всё-таки добавилась"
    assert status.visible and "Введите текст" in status.value, "нет подсказки о пустом вводе"

    # 3. Переключение чекбокса обновляет запись.
    first_row = tasks_list.controls[0]
    checkbox = first_row.controls[0]
    checkbox.value = not checkbox.value
    checkbox.on_change(None)
    assert fake.rows[0].done is True, "чекбокс не обновил задачу"

    # 4. Удаление.
    first_row.controls[2].on_click(None)
    assert fake.deleted, "кнопка удаления ничего не удалила"

    # 5. Ошибка сети показывается текстом, а не падением приложения.
    def boom() -> list[Task]:
        raise RepoError("Сработала RLS: нет политики на select")

    fake.list_tasks = boom  # type: ignore[assignment]
    error_page = FakePage()
    app.main(error_page)
    error_status = error_page.controls[2]
    assert "RLS" in (error_status.value or ""), "ошибка не показана пользователю"
    assert error_status.visible, "строка ошибки скрыта"

    print("OK: экран собран, CRUD-обработчики работают, ошибка выводится текстом")


if __name__ == "__main__":
    check()
