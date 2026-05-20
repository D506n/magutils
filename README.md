# MagUtils - библиотека полезных утилит для Python

Набор готовых функций и классов для Python приложений. Библиотека содержит инструменты для логирования, работы с JSON, планирования задач, интернационализации и других распространённых задач.

## Установка

```bash
uv add magutils
```

Или добавьте в `pyproject.toml`:

```toml
dependencies = ["magutils"]
```

## Документация

### Оглавление:
- [logging](#logging)
  - [config](#loggingconfig)
  - [formatters](#loggingformatters)
    - [colored_console](#loggingformatterscoloredconsole)
    - [monocolor](#loggingformattersmonocolor)
    - [json](#loggingformattersjson)
  - [handlers](#logginghandlers)
    - [console](#logginghandlersasyncconsolehandler)
    - [file](#logginghandlersasyncfilehandler)
- [utils](#utils)
  - [id](#utilsid)
  - [json_path](#utilsjson_path)
  - [singleton](#utilssingleton)
  - [time_utils](#utilstime_utils)
  - [bg_tasks](#utilsbg_tasks)
  - [schedulled_tasks](#utilsschedulled_tasks)
  - [i18n](#utilsi18n)
  - [tree_import](#utilstree_import)
  - [checkout_helper](#utilscheckout_helper)
  - [env_utils](#utilsenv_utils)

### logging

Модуль для настройки и управления логированием с поддержкой асинхронных обработчиков и различных форматеров.

### logging.config

Функция `config_async_logging` для настройки асинхронного логирования с поддержкой переменных окружения.

Параметры:
- `formatter`: экземпляр Formatter или None (по умолчанию используется ColoredConsoleFormatter)
- `level`: уровень логирования по умолчанию
- `handlers`: список обработчиков (если не указан, создаются на основе переменных окружения)
- `force`: принудительно применить конфигурацию ко всем существующим логгерам
- `env_prefix`: префикс для переменных окружения (например, "APP_" для `APP_LOG_LEVEL`)
- `mp_que`: очередь для многопроцессного логирования

Переменные окружения (можно использовать с префиксом через `env_prefix`):
- `LOG_LEVEL` - общий уровень логирования (по умолчанию INFO)
- `LOG_CONSOLE_LEVEL` - уровень логирования в консоль (по умолчанию равен `LOG_LEVEL`)
- `LOG_FILE_LEVEL` - уровень логирования в файл (по умолчанию равен `LOG_LEVEL`)
- `CONSOLE_LOG_LEVEL` - включить логирование в консоль (true/false, по умолчанию true)
- `CONSOLE_LOG_JSON` - использовать JSON формат в консоли (true/false)
- `LOG_CONSOLE_COLORS` - использовать цвета в консоли (true/false, по умолчанию true)
- `LOG_FILE` - включить запись в файл (true/false)
- `LOG_FILE_PATH` - путь к файлу лога (по умолчанию `data/log.log`)
- `LOG_FILE_MAXBYTES` - максимальный размер файла перед ротацией (в байтах)
- `LOG_FILE_ROTATION_BY_DT` - ротировать файлы по дате (true/false)
- `LOG_FILE_ON_EXPIRE` - действие при истечении срока хранения логов (`delete` или `archive`)
- `LOG_FILE_JSON` - использовать JSON формат в файле (true/false)
- `LOG_FORMAT` - формат строки лога (по умолчанию `%(asctime)s - %(name)s - %(levelname)s - %(message)s`)
- `LOG_TIME_FORMAT` - формат времени в логе (по умолчанию `%Y-%m-%d %H:%M:%S`)
- `LOG_USE_CACHE` - использовать кэш для форматирования (true/false, по умолчанию true)
- `LOG_NO_CUT` - не обрезать длинные строки логов (true/false, по умолчанию false)

Пример:
```python
from magutils.logging import config_async_logging

config_async_logging(level="DEBUG")
```

### logging.formatters

Модуль содержит несколько готовых форматтеров для логов:

#### logging.formatters.coloredconsole

`ColoredConsoleFormatter` - форматтер с цветным выводом в консоль, использует colorama для кроссплатформенной поддержки цветов.

Пример:
```python
from magutils.logging.formatters import ColoredConsoleFormatter

formatter = ColoredConsoleFormatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
```

#### logging.formatters.monocolor

`MonocolorFormatter` - монохромный форматтер для консоли без использования цветов.

#### logging.formatters.json

`JsonFormatter` - форматтер, который сериализует записи логов в JSON. Полезен для интеграции с системами сбора логов (ELK, Loki и т.д.).

Пример:
```python
from magutils.logging.formatters import JsonFormatter

formatter = JsonFormatter()
```

### logging.handlers

Асинхронные обработчики логов, которые не блокируют основной поток приложения.

#### logging.handlers.asyncconsolehandler

`AsyncConsoleHandler` - асинхронный обработчик для вывода логов в консоль.

Пример:
```python
from magutils.logging.handlers import AsyncConsoleHandler
from magutils.logging.formatters import ColoredConsoleFormatter

handler = AsyncConsoleHandler()
handler.setFormatter(ColoredConsoleFormatter())
```

#### logging.handlers.asyncfilehandler

`AsyncFileHandler` - асинхронный обработчик для записи логов в файл с поддержкой ротации по размеру или дате.

Параметры:
- `file_path`: путь к файлу лога (строка или Path)
- `max_bytes`: максимальный размер файла в байтах перед ротацией (опционально)
- `rotation_by_dt`: ротировать файлы по дате (создавать новый файл каждый день)
- `on_expire`: действие при ротации: `'delete'` (удалить) или `'compress'` (заархивировать)
- `compressor`: пользовательская функция компрессии (опционально)
- `buffer_size`: размер буфера для асинхронной записи (по умолчанию 500 строк)

Пример:
```python
from magutils.logging.handlers import AsyncFileHandler

handler = AsyncFileHandler(
    file_path="logs/app.log",
    max_bytes=10_000_000,  # 10 MB
    rotation_by_dt=True,
    on_expire='compress'
)
```

### utils

### utils.id

`def gen_id(alphabet: str = DEFAULT_ALPHABET, size: int = 15)`

Функция для генерации строк ID работает на основе алгоритма NanoID. Стандартный алфавит: `abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`
Такие ID остаются весьма уникальными, при более короткой строке чем uuid4. Калькулятор уникальности: https://zelark.github.io/nano-id-cc/
С параметрами которые выставлены в функции по умолчанию, для вероятности коллизии 1% нужно сгенерировать 3 триллиона ID.

Пример:

```python
from magutils.id import gen_id

for _ in range(10):
    print(gen_id())

# >>> 9VkeORlHnV1pMjA
# >>> 5WPGxwzkUq1uhsf
# >>> jzBKy3oTshI8ABB
# >>> RjzcPqEM5v7hhip
# >>> he7ldhY0upiNrCg
# >>> aSzH7nXQtrND7QG
# >>> LkEJuotny94FpPM
# >>> 459YeBcpmMZOqcw
# >>> 36zjHPRVkKPfjbc
# >>> 8FlKsU3hWVQOiBE
```

### utils.json_path

Модуль для работы с JSON-подобными структурами данных (словари и списки) с использованием строковых путей. Поддерживает сложные операции: получение, установка, удаление, форматирование, а также wildcard-обход и хуки.

#### Синтаксис путей

Путь состоит из последовательности ключей, разделённых точкой. Поддерживаются следующие типы ключей:

- **Имя поля** (`"field"`) – доступ к ключу словаря.
- **Числовой индекс** (`0`, `-1`) – доступ к элементу списка (отрицательные индексы поддерживаются).
- **Wildcard** (`*`) – соответствует любому элементу на данном уровне (используется для обхода массивов).
- **Специальный ключ** (`!append`) – добавляет новый элемент в конец списка (только для операций записи).

#### Основные компоненты модуля

- **`Walker`** – ядро модуля, выполняет обход структуры по пути с учётом wildcard.
- **`Intent`** (`Get`, `Set`, `Del`) – определяет намерение операции (получить, установить, удалить).
- **`Ctx`** – контекст выполнения, хранит текущие данные, позицию и результат.
- **`hooks`** – система хуков для кастомизации поведения на каждом шаге.
- **`builder`** – преобразует строковый путь во внутреннее представление.
- **`states`** – управляет состояниями автомата, обрабатывающего путь.

#### Функции верхнего уровня

##### `get_by_path(path: str, data: dict | list, default: Any = None, silent: bool = True) -> Any`

Извлекает значение по пути. Если путь не существует и `silent=True`, возвращает `default`. Если `silent=False`, вызывает `KeyError`.

##### `set_by_path(path: str, data: dict | list, value: Any, silent: bool = True) -> None`

Устанавливает значение по пути. Создаёт недостающие промежуточные узлы (словари или списки) автоматически.

##### `del_by_path(path: str, data: dict | list, silent: bool = True) -> None`

Удаляет элемент по пути. Если элемент не существует и `silent=True`, игнорирует операцию; иначе вызывает `KeyError`.

##### `rebuild(path: str, data: dict | list, new_data: dict | list, silent: bool = True) -> None`

Заменяет подструктуру по пути на `new_data`.

##### `format(template: str, data: dict) -> str`

Заменяет в строке плейсхолдеры `{путь}` на значения из `data`. Поддерживает wildcard и индексы.

#### Класс `Walker`

Позволяет создавать предварительно скомпилированные объекты для многократного использования одного пути.

```python
from magutils.json_path import Walker, Get, Set, Del

walker = Walker('users.*.name', Get)
result = walker.walk(data)  # возвращает контекст с найденными значениями
```

#### Примеры использования

```python
from magutils.json_path import get_by_path, set_by_path, del_by_path, format

data = {
    'store': {
        'books': [
            {'title': 'Python Crash Course', 'price': 39.99},
            {'title': 'Fluent Python', 'price': 49.99}
        ],
        'location': 'Moscow'
    }
}

# Простое получение
print(get_by_path('store.books.0.title', data))  # Python Crash Course

# Wildcard-обход (получить все названия книг)
print(get_by_path('store.books.*.title', data))  # ['Python Crash Course', 'Fluent Python']

# Установка значения
set_by_path('store.books.1.price', data, 45.50)
set_by_path('store.books.!append', data, {'title': 'Deep Learning', 'price': 89.99})

# Удаление
del_by_path('store.location', data)

# Форматирование с wildcard
template = 'Books: {store.books.*.title}'
print(format(template, data))  # Books: ['Python Crash Course', 'Fluent Python', 'Deep Learning']

# Работа через Walker
from magutils.json_path import Walker, Get
walker = Walker('store.books.*.price', Get)
ctx = walker.walk(data)
print(ctx.result)  # [39.99, 45.5, 89.99]
```

#### Особенности

- **Кэширование**: `Walker` кэширует скомпилированные пути для повторного использования.
- **Типизация**: поддерживает generics для работы с типизированными структурами.

### utils.singleton

`def singleton(cls)`

Декоратор который делает декорируемый класс синглтоном.

Пример:

```python
from magutils.singleton import singleton

@singleton
class Example():
    def __init__(self):
        self.a = 1

e1 = Example()
e2 = Example()
e1.a = 2
print(e2.a)
# >>> 2
print(e1 is e2)
# >>> True
```

### utils.time_utils

Модуль для работы со временем, включает функции для парсинга, форматирования, преобразования временных меток и измерения производительности.

Основные функции:

- `get_tz()` – возвращает объект часового пояса на основе переменной окружения `TIMEZONE` (по умолчанию UTC)
- `get_current_time()` – возвращает текущее время с учётом часового пояса
- `parse_time(time_str, format_str=None)` – парсит строку времени в объект `datetime`. Формат по умолчанию задаётся переменной окружения `TIME_FORMAT`
- `format_time(time_obj, format_str=None)` – форматирует объект `datetime` в строку
- `get_delta(dt, dt2=None)` – вычисляет разницу между двумя временами (`timedelta`). Если `dt2` не указан, используется текущее время
- `seconds_stringify(seconds)` – преобразует количество секунд в человекочитаемую строку (часы и минуты)
- `ns_stringify(ns)` – преобразует количество наносекунд в строку с единицами (s, ms, µs, ns)
- `from_timestamp(timestamp)` – создаёт `datetime` из Unix-временной метки (int/float) с учётом часового пояса
- `get_future_time(delta)` – возвращает время, которое наступит через `delta` секунд от текущего момента
- `perf_counter(handler=print)` – декоратор для измерения времени выполнения функции (синхронной или асинхронной). Результат передаётся в `handler`

Примеры:

```python
from magutils.time_utils import (
    get_current_time, parse_time, format_time, get_delta,
    seconds_stringify, ns_stringify, from_timestamp, get_future_time,
    perf_counter
)
import asyncio

# Часовой пояс и текущее время
print(get_current_time())  # 2026-05-20 19:23:10.123456+03:00

# Парсинг и форматирование
dt = parse_time("2025-12-31T23:59:59.000000+00:00")
print(format_time(dt, "%Y-%m-%d %H:%M:%S"))  # 2025-12-31 23:59:59

# Разница во времени
delta = get_delta(dt)
print(delta)  # 123 days, 4:32:10.123456

# Преобразование секунд и наносекунд
print(seconds_stringify(3665))  # 1 h. 1 m.
print(ns_stringify(1_234_567_890))  # 1 s 234 ms 567 µs 890 ns

# Работа с временными метками
print(from_timestamp(1700000000))

# Время в будущем
print(get_future_time(3600))  # через час

# Измерение производительности
@perf_counter()
def slow_function():
    time.sleep(0.1)

slow_function()  # Выведет: slow_function: 100 ms 234 µs 567 ns

@perf_counter()
async def async_task():
    await asyncio.sleep(0.05)

asyncio.run(async_task())  # Выведет: async_task: 50 ms 123 µs 456 ns
```

### utils.bg_tasks

Класс `BgTask` для управления фоновыми асинхронными задачами. Позволяет запускать корутины в фоне и автоматически обрабатывать ошибки.

Пример:

```python
from magutils.bg_tasks import BgTask
import asyncio

async def my_task():
    await asyncio.sleep(1)
    print("Task completed")

BgTask.create(my_task())
```

### utils.schedulled_tasks

Модуль для планирования задач по cron-расписанию. Класс `ScheduledTask` позволяет создавать задачи, которые выполняются по расписанию с поддержкой подписчиков.

Пример:

```python
from magutils.schedulled_tasks import ScheduledTask
import asyncio

async def job(payload):
    print(f"Job executed with payload: {payload}")

task = ScheduledTask("* * * * *", {"data": "test"})
task.subscribe("my_job", job)
task.schedule()
```

### utils.i18n

Модуль интернационализации с поддержкой множественных форм, загрузки переводов из JSON/YAML файлов и автоматического обновления при изменении файлов.

Основной класс `I18n`:

```python
from magutils.i18n import I18n
from pathlib import Path

i18n = I18n(Path("locales"), falllang="en")
translation = i18n.get("key.path", lang="ru", count=5)
```

### utils.tree_import

Модуль для автоматической загрузки компонентов приложения, организованных в виде дерева директорий. Особенно полезен для регистрации маршрутов FastAPI, обработчиков телеграм-ботов (Telegrinder) и плагинов.

#### Высокоуровневые функции

##### `build_root_fastapi(path: Path, file_name: str = 'api_router.py', skip_err: bool = False) -> fastapi.APIRouter`

Создаёт корневой `APIRouter`, который автоматически включает все роутеры, найденные в поддиректориях. Каждая поддиректория должна содержать файл `api_router.py` (или указанное имя) с экземпляром `APIRouter`.

Пример структуры проекта:

```
routes/
├── users/
│   └── api_router.py
├── posts/
│   └── api_router.py
└── admin/
    └── api_router.py
```

Использование:

```python
from fastapi import FastAPI
from magutils.tree_import import build_root_fastapi
from pathlib import Path

app = FastAPI()

# Автоматически собираем все роутеры из директории routes
root_router = build_root_fastapi(Path("routes"))
app.include_router(root_router)

# Теперь все маршруты из users, posts, admin доступны
```

Содержимое `routes/users/api_router.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
async def list_users():
    return [{"id": 1, "name": "Alice"}]
```

##### `build_root_telegrinder(path: Path, file_name: str = 'disp.py', skip_err: bool = False) -> telegrinder.Dispatch`

Аналогично собирает диспетчеры для библиотеки Telegrinder (Telegram бот).

##### `build_root(entity_type: type, root_path: Path, mod_name: str, add_name: str = 'load', skip_err: bool = False, **kwargs)`

Универсальная функция для построения дерева любого типа, поддерживающего метод добавления дочерних компонентов (например, `include_router` у APIRouter, `load` у Dispatch).

#### Низкоуровневая функция `import_tree`

`import_tree(path: Path, target_class: type, skip_errors: bool = False, max_depth: int = None) -> list`

Рекурсивно обходит директорию, импортирует все Python-модули и возвращает список экземпляров `target_class` (или его подклассов).

Пример загрузки плагинов:

```python
from magutils.tree_import import import_tree
from pathlib import Path

class Plugin:
    def run(self):
        pass

plugins = import_tree(Path("plugins"), Plugin)
for plugin in plugins:
    plugin.run()
```

#### Особенности

- **Кэширование импорта**: каждый модуль импортируется только один раз.
- **Гибкая настройка**: можно указать имя файла, метод добавления, обрабатывать ошибки.
- **Поддержка вложенных структур**: рекурсивный обход поддиректорий.

Модуль идеально подходит для поддержания чистоты архитектуры в больших проектах, где компоненты распределены по отдельным папкам.

### utils.checkout_helper

Утилита для помощи при переключении веток в Git с поддержкой миграций между ветками. Использует конфигурационный файл `checkout.json` для определения правил миграции.

Использование:

```bash
python -m magutils.checkout_helper --migration main>demo
```

### utils.env_utils

Модуль для работы с переменными окружения, включая валидацию, загрузку из `.env` файлов, YAML конфигураций и интеграцию с Kubernetes. Основан на декораторе `environ` и функции `field`.

#### Основные компоненты

- **Декоратор `environ`** – оборачивает класс, превращая его в синглтон с автоматической загрузкой переменных окружения.
- **Функция `field`** – определяет поле конфигурации с возможностью указания значения по умолчанию, фабрики значений, алиасов.
- **Расширение `yaml`** – предоставляет фабрику для загрузки значений из YAML файлов.
- **Расширение `k8s`** – интеграция с Kubernetes Secrets (опционально).

#### Использование

Базовый пример:

```python
from magutils.env_utils import environ, field

@environ()
class AppConfig:
    DEBUG: bool = field(default=False)
    DATABASE_URL: str = field()
    PORT: int = field(default=8000)
    LOG_LEVEL: str = field(default='INFO', aliases=['LOGLEVEL'])

config = AppConfig()
print(config.DATABASE_URL)  # значение из переменной окружения DATABASE_URL
```

- Поля без `default` являются обязательными – если переменная окружения не найдена, будет вызвано исключение.
- `aliases` позволяет указать дополнительные имена переменных окружения (например, `LOGLEVEL` вместо `LOG_LEVEL`).
- Декоратор `environ` автоматически загружает `.env` файл (рекурсивно ищет его в родительских директориях).

#### Загрузка значений из YAML

```python
from magutils.env_utils import environ, field
from magutils.env_utils.ext.yaml_ import yaml

@environ()
class YamlConfig:
    # Загрузка значения из config.yaml по пути 'database.host'
    DB_HOST: str = field(default_factory=yaml('config.yaml', 'database.host'))
    # Значение по умолчанию, если путь не существует
    DB_PORT: int = field(default_factory=yaml('config.yaml', 'database.port', default=5432))

config = YamlConfig()
```

Функция `yaml` возвращает фабрику, которая при первом обращении читает YAML файл и извлекает значение по указанному пути.

#### Интеграция с Kubernetes Secrets

Требуется установка дополнительных зависимостей (группа `k8s`). Пример:

```python
from magutils.env_utils import environ, field
from magutils.env_utils.ext.k8s import k8s_secret

@environ()
class K8sConfig:
    SECRET_TOKEN: str = field(default_factory=k8s_secret('my-secret', 'token'))
```

#### Кастомизация

Декоратор `environ` принимает параметры:

- `env_path` – явный путь к `.env` файлу (по умолчанию ищет автоматически).
- `prefix` – префикс для всех переменных окружения (например, `prefix='APP_'` заставит искать `APP_DATABASE_URL`).

Пример:

```python
@environ(prefix='APP_')
class PrefixedConfig:
    VALUE: str = field()
```

#### Валидация типов

Модуль использует `pydantic.TypeAdapter` для валидации и преобразования типов. Поддерживаются сложные типы (`list`, `dict`, `Union` и т.д.) через аннотации.

```python
from typing import List

@environ()
class ComplexConfig:
    ALLOWED_HOSTS: List[str] = field(default_factory=lambda: ['localhost'])
    # Переменная окружения ALLOWED_HOSTS должна содержать JSON-массив строк
```

## Лицензия

Проект распространяется под лицензией MIT. Подробнее см. файл LICENSE.
