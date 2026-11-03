"""Экран «Список задач»: CRUD в Supabase через supabase-py.

Здесь только интерфейс: все сетевые вызовы и ошибки инкапсулированы
в repo.py. Запуск на десктопе:

    flet run src/main.py
"""

from __future__ import annotations

import flet as ft

from repo import RepoError, Task, TaskRepo

ERROR_COLOR = "#c62828"
MUTED_COLOR = "#616161"


def main(page: ft.Page) -> None:
    page.title = "Список задач"
    page.padding = 16

    # Подключение к Supabase. Если ключи не настроены, показываем
    # отдельный экран, а не падаем с traceback.
    try:
        repo = TaskRepo()
    except RepoError as exc:
        page.add(
            ft.Text("Нет подключения к Supabase", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(str(exc), color=ERROR_COLOR),
        )
        return

    # --- обработчики ----------------------------------------------------
    # Объявлены до контролов: имена field/status/etc. берутся из области
    # видимости в момент вызова, поэтому порядок объявления безопасен.

    def show_error(message: str) -> None:
        status.value = message
        status.visible = True
        page.update()

    def hide_status() -> None:
        status.value = ""
        status.visible = False

    def refresh() -> None:
        """Перечитывает список из Supabase и перерисовывает его."""
        try:
            tasks = repo.list_tasks()
        except RepoError as exc:
            tasks_list.controls = []
            counter.value = ""
            page.update()
            show_error(str(exc))
            return

        if tasks:
            tasks_list.controls = [build_row(task) for task in tasks]
            done_count = sum(1 for task in tasks if task.done)
            counter.value = f"Всего: {len(tasks)} · выполнено: {done_count}"
        else:
            tasks_list.controls = [
                ft.Text("Пока пусто — добавьте первую задачу.", color=MUTED_COLOR)
            ]
            counter.value = "Всего: 0"
        page.update()

    def on_add(_event=None) -> None:
        """Добавляет задачу из текстового поля."""
        title = (field.value or "").strip()
        if not title:
            show_error("Введите текст задачи.")
            return
        try:
            repo.add_task(title)
        except RepoError as exc:
            show_error(str(exc))
            return
        field.value = ""
        hide_status()
        refresh()

    def on_toggle(task: Task, checked: bool) -> None:
        """Переключает отметку «выполнено»."""
        try:
            repo.set_done(task.id, bool(checked))
        except RepoError as exc:
            show_error(str(exc))
        refresh()

    def on_delete(task: Task) -> None:
        """Удаляет задачу."""
        try:
            repo.delete_task(task.id)
        except RepoError as exc:
            show_error(str(exc))
        refresh()

    def build_row(task: Task) -> ft.Row:
        """Одна строка списка: чекбокс, текст, кнопка удаления."""
        label = ft.Text(task.title, expand=True, size=16)
        if task.done:
            label.color = MUTED_COLOR
            label.italic = True

        # Новое состояние читаем из самого чекбокса, а не из объекта события:
        # так обработчик не зависит от внутреннего устройства Event в Flet.
        checkbox = ft.Checkbox(value=task.done)
        checkbox.on_change = lambda _event: on_toggle(task, bool(checkbox.value))

        return ft.Row(
            controls=[
                checkbox,
                label,
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_color=ERROR_COLOR,
                    tooltip="Удалить",
                    on_click=lambda _event: on_delete(task),
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # --- контролы -------------------------------------------------------
    field = ft.TextField(
        hint_text="Что нужно сделать?",
        expand=True,
        autofocus=True,
        on_submit=on_add,
    )
    add_button = ft.IconButton(
        icon=ft.Icons.ADD,
        tooltip="Добавить задачу",
        on_click=on_add,
    )
    status = ft.Text("", size=13, color=ERROR_COLOR, visible=False)
    tasks_list = ft.ListView(expand=True, spacing=8)
    counter = ft.Text("", size=13, color=MUTED_COLOR)

    # --- разметка экрана ------------------------------------------------
    page.add(
        ft.Text("Список задач", size=22, weight=ft.FontWeight.BOLD),
        ft.Row(
            controls=[field, add_button],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        status,
        ft.Divider(),
        tasks_list,
        counter,
    )

    refresh()


if __name__ == "__main__":
    ft.run(main)
