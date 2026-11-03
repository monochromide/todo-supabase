"""Шаблон конфигурации.

1. Скопируйте этот файл в `src/config.py`:
       copy src\\config.example.py src\\config.py      (Windows)
       cp src/config.example.py src/config.py          (Linux/macOS)
2. Вставьте значения, которые Supabase показывает в диалоге **Connect**
   (кнопка в шапке проекта) или в разделе **Settings → API Keys**:

   - Project URL  → SUPABASE_URL        (только база, без /rest/v1)
   - публичный ключ → SUPABASE_ANON_KEY  (`sb_publishable_…` или legacy `eyJ…`)

   Имя переменной оставлено историческим: подойдёт любой публичный ключ.
   Формат `sb_publishable_…` предпочтителен — Supabase сворачивает
   поддержку `anon`/`service_role` к концу 2026 года.

`src/config.py` перечислен в .gitignore и в репозиторий не попадает.
В GitHub Actions он генерируется из секретов SUPABASE_URL и
SUPABASE_ANON_KEY (см. .github/workflows/build-apk.yml).

secret key (`sb_secret_…`) и service_role сюда вставлять НЕЛЬЗЯ: они обходят RLS.
"""

SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_ANON_KEY = "<publishable key или legacy anon key>"
