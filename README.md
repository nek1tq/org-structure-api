# Org Structure API

REST API для управления организационной структурой: иерархия подразделений и сотрудники в них. Стек: FastAPI (async), SQLAlchemy 2.0, PostgreSQL, Alembic. Полностью контейнеризовано через Docker.

## Содержание

- [Возможности](#возможности)
- [Стек технологий](#стек-технологий)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Локальная разработка (без Docker)](#локальная-разработка-без-docker)
- [Описание API](#описание-api)
- [Структура проекта](#структура-проекта)
- [Бизнес-правила](#бизнес-правила)
- [Схема БД](#схема-бд)
- [Тестирование](#тестирование)
- [Миграции](#миграции)
- [Конфигурация](#конфигурация)

## Возможности

- Подразделения в виде дерева с произвольной вложенностью (self-referencing FK).
- Сотрудники привязаны к одному подразделению.
- Получение поддерева с настраиваемой глубиной (RECURSIVE CTE в Postgres, рекурсивный CTE в SQLite для тестов).
- Два режима удаления: `cascade` и `reassign`.
- Защита от циклов при перемещении подразделений.
- Валидация на Pydantic v2: триминг имён, длина 1..200, уникальность `(parent_id, name)`.
- Async-first стек (`asyncpg` в проде, `aiosqlite` для тестов).
- Слоистая архитектура: routers → services → repositories.
- Документация OpenAPI: Swagger UI на `/docs`, ReDoc на `/redoc`.

## Стек технологий

| Слой        | Решение                                       |
|-------------|-----------------------------------------------|
| Язык        | Python 3.12 (поддерживается 3.11+)            |
| Фреймворк   | FastAPI 0.115+                                |
| Валидация   | Pydantic v2 + pydantic-settings               |
| ORM         | SQLAlchemy 2.0 (async)                        |
| СУБД        | PostgreSQL 16                                 |
| Драйвер     | asyncpg                                       |
| Миграции    | Alembic (async env)                           |
| Тесты       | pytest, pytest-asyncio, httpx, aiosqlite      |
| Менеджер    | Poetry                                        |
| Контейнер   | Docker (multi-stage), docker-compose          |

## Быстрый старт (Docker)

Требования: Docker Desktop (или Docker Engine + Compose v2).

```bash
git clone https://github.com/<your-username>/org-structure-api.git
cd org-structure-api
cp .env.example .env
docker compose up --build
```

API будет доступен на `http://localhost:8000`. Миграции применяются автоматически при старте контейнера.

Интерактивная документация:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

Остановить контейнеры:

```bash
docker compose down              # остановить
docker compose down -v           # остановить и удалить том Postgres
```

## Локальная разработка (без Docker)

Требования: Python 3.11+ и Poetry (или pip + venv).

```bash
git clone https://github.com/<your-username>/org-structure-api.git
cd org-structure-api

# Вариант A — Poetry
poetry install
poetry shell

# Вариант B — pip + venv
python -m venv .venv
.\.venv\Scripts\activate     # PowerShell в Windows
# source .venv/bin/activate  # Linux/macOS
pip install -e .             # или установить зависимости явно (см. pyproject.toml)
```

Настроить окружение (направить на локальный Postgres):

```bash
cp .env.example .env
# отредактировать .env: указать DATABASE_URL, например
# DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/org_structure
```

Применить миграции и запустить сервер:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

## Описание API

Базовый префикс: `/`

### Создать подразделение

`POST /departments/`

```json
{ "name": "Engineering", "parent_id": null }
```

`201 Created` → `DepartmentResponse`. `404`, если `parent_id` не существует. `409`, если подразделение с таким именем уже есть у того же родителя.

### Создать сотрудника в подразделении

`POST /departments/{id}/employees/`

```json
{ "full_name": "Alice Johnson", "position": "Senior Engineer", "hired_at": "2024-01-15" }
```

`201 Created` → `EmployeeResponse`. `404`, если подразделение не существует. `hired_at` опционально.

### Получить подразделение (со сотрудниками и поддеревом)

`GET /departments/{id}?depth=1&include_employees=true&employee_sort=created_at`

Параметры запроса:

| Параметр            | Тип     | По умолчанию   | Описание                                |
|---------------------|---------|----------------|-----------------------------------------|
| `depth`             | int     | `1`            | 0..5, глубина вложенных подразделений   |
| `include_employees` | bool    | `true`         | Включать ли сотрудников в каждый узел   |
| `employee_sort`     | enum    | `created_at`   | `created_at` или `full_name`            |

`200 OK` → `DepartmentTree`. `404`, если не найдено.

### Переименовать или переместить подразделение

`PATCH /departments/{id}`

```json
{ "name": "R&D", "parent_id": 7 }
```

Оба поля опциональны. Если передать `parent_id: null` — подразделение перемещается в корень. `409`, если это создаст цикл (перемещение в собственное поддерево) или дубль имени у нового родителя.

### Удалить подразделение

`DELETE /departments/{id}?mode=cascade`

`DELETE /departments/{id}?mode=reassign&reassign_to_department_id=42`

| Режим      | Эффект                                                                                |
|------------|---------------------------------------------------------------------------------------|
| `cascade`  | Удаляет подразделение, всех потомков и всех их сотрудников                            |
| `reassign` | Переводит прямых сотрудников в `reassign_to_department_id`, затем удаляет подразделение |

`204 No Content` при успехе. `400`, если для `mode=reassign` не указан `reassign_to_department_id`. `409`, если `mode=reassign` применён к подразделению с дочерними (нужно либо `cascade`, либо предварительно перенести/удалить детей).

## Структура проекта

```
org-structure-api/
├── app/
│   ├── api/
│   │   ├── deps.py                  # FastAPI-зависимости (session, services)
│   │   ├── exception_handlers.py    # Доменные ошибки → HTTP-ответы
│   │   └── v1/departments.py        # Роуты
│   ├── core/
│   │   ├── config.py                # Pydantic Settings
│   │   ├── database.py              # Async engine, session, Base
│   │   └── logging.py               # Настройка логирования
│   ├── models/                      # SQLAlchemy ORM-модели
│   ├── schemas/                     # Pydantic v2 request/response модели
│   ├── repositories/                # Доступ к БД (запросы, CRUD)
│   ├── services/                    # Бизнес-логика
│   ├── exceptions.py                # Доменные исключения
│   └── main.py                      # Фабрика приложения
├── alembic/
│   ├── env.py                       # Async-aware Alembic env
│   └── versions/0001_initial.py     # Начальная схема
├── tests/
│   ├── conftest.py                  # Async-фикстуры, in-memory SQLite
│   ├── test_departments.py
│   └── test_employees.py
├── Dockerfile                       # Multi-stage, non-root, healthcheck
├── docker-compose.yml               # API + Postgres с healthchecks
├── alembic.ini
├── pyproject.toml
├── .env.example
└── README.md
```

## Бизнес-правила

- `name` подразделения триммится; после триминга длина 1..200 символов.
- `(parent_id, name)` уникальны — двух подразделений с одинаковым именем у одного родителя быть не может.
- Подразделение не может быть собственным родителем.
- Подразделение нельзя переместить внутрь собственного поддерева (защита от циклов).
- `full_name` и `position` сотрудника триммятся; оба 1..200 символов.
- `hired_at` опционально.
- Режим `cascade` опирается на `ON DELETE CASCADE` на уровне БД.
- Режим `reassign` требует существующего целевого подразделения и отсутствия детей у удаляемого.

## Схема БД

```
departments
├── id              SERIAL PRIMARY KEY
├── name            VARCHAR(200) NOT NULL                CHECK length(name) BETWEEN 1 AND 200
├── parent_id       INT NULL REFERENCES departments(id)  ON DELETE CASCADE
├── created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
├── UNIQUE (parent_id, name)
├── CHECK parent_id IS NULL OR parent_id <> id
└── INDEX (parent_id)

employees
├── id              SERIAL PRIMARY KEY
├── department_id   INT NOT NULL REFERENCES departments(id) ON DELETE CASCADE
├── full_name       VARCHAR(200) NOT NULL                CHECK length(full_name) BETWEEN 1 AND 200
├── position        VARCHAR(200) NOT NULL                CHECK length(position) BETWEEN 1 AND 200
├── hired_at        DATE NULL
├── created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
└── INDEX (department_id)
```

## Тестирование

Тесты исполняются на in-memory SQLite через `aiosqlite` — Postgres или Docker для тестов не требуются:

```bash
# В venv проекта
pytest                                # все тесты
pytest tests/test_departments.py      # один файл
pytest -k cycle                       # по подстроке имени
pytest -v                             # подробный вывод
```

Что покрыто:

- Создание подразделений (корень, дочернее, дубль имени, несуществующий родитель).
- Триминг имён и отбраковка пустых.
- Получение дерева с `depth`, `include_employees`, `employee_sort`.
- Переименование, перемещение, защита от циклов, защита от self-parent.
- Каскадное удаление (потомки и их сотрудники исчезают).
- Удаление с переводом (сотрудники переходят, проверка target-а и наличия детей).

## Миграции

```bash
# Применить все pending-миграции
alembic upgrade head

# Сгенерировать новую миграцию по изменениям моделей
alembic revision --autogenerate -m "add something"

# Откатить один шаг
alembic downgrade -1

# История миграций
alembic history
```

В Docker контейнер API при старте выполняет `alembic upgrade head` перед запуском Uvicorn.

## Конфигурация

Конфигурируется через переменные окружения (см. `.env.example`):

| Переменная          | По умолчанию                                                            | Назначение                              |
|---------------------|-------------------------------------------------------------------------|-----------------------------------------|
| `DATABASE_URL`      | `postgresql+asyncpg://postgres:postgres@localhost:5432/org_structure`   | Async DSN для SQLAlchemy                |
| `LOG_LEVEL`         | `INFO`                                                                  | Уровень логирования                     |
| `DEBUG`             | `False`                                                                 | Debug-режим FastAPI                     |
| `POSTGRES_USER`     | `postgres`                                                              | Используется docker-compose для Postgres |
| `POSTGRES_PASSWORD` | `postgres`                                                              | Используется docker-compose для Postgres |
| `POSTGRES_DB`       | `org_structure`                                                         | Используется docker-compose для Postgres |
| `POSTGRES_PORT`     | `5432`                                                                  | Маппинг порта на хосте                  |
| `API_PORT`          | `8000`                                                                  | Маппинг порта API на хосте              |
