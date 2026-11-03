-- Схема и политики доступа для приложения «Список задач».
-- Выполнить целиком в Supabase → SQL Editor → Run.
--
-- Клиент ходит в базу напрямую с anon-ключом, без промежуточного сервера,
-- поэтому безопасность держится только на RLS-политиках ниже.

-- 1. Таблица -----------------------------------------------------------------

create table if not exists public.tasks (
    id          uuid primary key default gen_random_uuid(),
    title       text not null check (length(btrim(title)) > 0),
    done        boolean not null default false,
    created_at  timestamptz not null default now()
);

comment on table public.tasks is 'Задачи учебного приложения (Flet + Supabase)';

-- Список строится по created_at desc, поэтому индексируем это поле.
create index if not exists tasks_created_at_idx
    on public.tasks (created_at desc);

-- 2. Row Level Security -------------------------------------------------------

alter table public.tasks enable row level security;

-- Права уровня таблицы для роли anon (под ней работает anon-ключ).
-- В Supabase они выданы по умолчанию, но явный grant делает поведение
-- предсказуемым, если схему пересоздают.
grant select, insert, update, delete on public.tasks to anon;

-- 3. Политики для CRUD --------------------------------------------------------
-- Политика = "что разрешено роли". Без политик RLS отвечает пустым списком
-- на select и ошибкой 42501 на insert/update/delete — это самая частая
-- причина "supabase-py ничего не возвращает".
--
-- Для учебного проекта доступ анонимному ключу открыт полностью.
-- В реальном приложении вместо true здесь было бы auth.uid() = user_id.

drop policy if exists tasks_select_anon on public.tasks;
create policy tasks_select_anon
    on public.tasks
    for select
    to anon
    using (true);

drop policy if exists tasks_insert_anon on public.tasks;
create policy tasks_insert_anon
    on public.tasks
    for insert
    to anon
    with check (true);

drop policy if exists tasks_update_anon on public.tasks;
create policy tasks_update_anon
    on public.tasks
    for update
    to anon
    using (true)
    with check (true);

drop policy if exists tasks_delete_anon on public.tasks;
create policy tasks_delete_anon
    on public.tasks
    for delete
    to anon
    using (true);

-- 4. Самопроверка -------------------------------------------------------------
-- Должно вернуть 4 строки (select/insert/update/delete):
--
--   select cmd, policyname from pg_policies
--   where schemaname = 'public' and tablename = 'tasks'
--   order by cmd;
