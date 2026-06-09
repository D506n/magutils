# MagUtils - библиотека полезных утилит для Python

Набор готовых функций и классов для Python приложений. Библиотека содержит инструменты для логирования, работы с JSON, планирования задач, интернационализации и других распространённых задач.

## Протестированные версии Python:

- 3.14
- 3.13
- 3.12

## Установка

```bash
uv add git+https://github.com/D506n/magutils
```

Или в pyproject.toml

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
  - [pubsub](#utilspubsub)
  - [req_limit](#utilsreq_limit)
  - [schedulled_tasks](#utilsschedulled_tasks)
  - [i18n](#utilsi18n)
  - [tree_import](#utilstree_import)
  - [checkout_helper](#utilscheckout_helper)
  - [env](#utilsenv)
  - [jwt](#utilsjwt)
  - [starlark](#utilsstarlark)
  - [fsm](#utilsfsm)
  - [pipeline](#utilspipeline)

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

### utils.pubsub

Класс `PubSub` для реализации системы событий (паттерн «Наблюдатель»). Позволяет подписываться на события асинхронными колбэками и эмитировать события с передачей полезной нагрузки.

Пример:

```python
from magutils.pubsub import PubSub
import asyncio

async def handler(payload):
    print(f"Received: {payload}")

event = PubSub[dict]()
unsubscribe = event.subscribe(handler)
event.emit({"data": "test"})
await asyncio.sleep(0.1)  # дать время на выполнение асинхронных задач
unsubscribe()
```

Методы:
- `subscribe(callback)` – подписывает асинхронный колбэк, возвращает функцию для отписки.
- `emit(payload, raise_errors=False)` – эмитирует событие, вызывая все подписанные колбэки.
- `unsubscribe(key)` – внутренний метод для отписки по ключу.

### utils.req_limit

Класс `Limiter` — синглтон для асинхронного ограничения частоты запросов (rate limiting) на основе `aiolimiter.AsyncLimiter`. Позволяет создавать именованные лимитеры с разными параметрами и использовать их как асинхронные контекстные менеджеры.

Пример:

```python
from magutils.req_limit import Limiter
import asyncio

# Создание лимитера: не более 5 запросов в секунду
Limiter.set("api", limit=5, per=1)

# Использование как контекстного менеджера
async with Limiter.rate_limit("api"):
    # выполнение запроса
    pass

# Если лимитер не был создан явно, get() создаст его с параметрами по умолчанию (10 запросов в секунду)
limiter = Limiter.get("default_limited")
```

Методы:
- `inst()` — возвращает экземпляр синглтона.
- `set(key, limit=10, per=1)` — создаёт лимитер для ключа с указанным лимитом (`limit` запросов за `per` секунд).
- `get(key)` — возвращает существующий лимитер для ключа или создаёт новый с параметрами по умолчанию (10 запросов/сек).
- `rate_limit(key)` — асинхронный контекстный менеджер, который приостанавливает выполнение при превышении лимита.

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

Модуль интернационализации с поддержкой множественных форм (плюрализация) через правила CLDR, загрузкой переводов из JSON/YAML файлов и автоматическим обновлением при изменении файлов.

Основной класс – `I18n` (синглтон, реализован через декоратор `@singleton`).

#### Инициализация

```python
from magutils.i18n import I18n
from pathlib import Path

# Первый вызов создаёт экземпляр с указанными параметрами
i18n = I18n(
    locdir=Path("locales"),
    plural_rules_path=Path("custom_plurals.json"),  # опционально можно указать файл с кастомными правилами плюрализации
    scan_ttl=10.0,  # время в секундах до повторного сканирования директории
    custom_validators=[],  # список кастомных валидаторов, валидаторы появлятся в будущих обновлениях
)

# Последующие вызовы с любыми параметрами возвращают тот же экземпляр
i18n2 = I18n()  # i18n2 is i18n
```

**Параметры конструктора**:

- `locdir` (обязательный при первом вызове) – путь к директории с файлами переводов (должна существовать).
- `plural_rules_path` (опционально) – путь к JSON-файлу с правилами плюрализации CLDR. По умолчанию используется встроенный файл `plurals.json` со списком из 224 языков из [CLDR_48](https://github.com/unicode-org/cldr/releases/tag/release-48).
- `scan_ttl` (опционально) – время в секундах, по истечении которого при отсутствии языка будет выполнено повторное сканирование директории. По умолчанию 10.0.
- `custom_validators` (опционально) – список функций‑валидаторов `TVALIDATOR`. Каждая функция принимает `(data: dict, file: Path)` и возвращает `bool`. Если валидатор возвращает `False`, файл игнорируется. (Валидаторы будут добавлены в будущих обновлениях)

#### Структура файлов переводов

Директория `locales` должна содержать файлы с именами вида `<язык>.<расширение>`. Поддерживаемые расширения: `.json`, `.yaml`, `.yml`.

Пример `locales/en.json`:
```json
{
    "hello": "Hello, {name}!",
    "nested": {
        "key": "Nested value"
    },
    "plural": {
        "one": "You have {count} apple",
        "other": "You have {count} apples"
    }
}
```

Пример `locales/ru.yaml`:
```yaml
hello: "Привет, {name}!"
nested:
  key: "Вложенное значение"
plural:
  one: "У вас {count} яблоко"
  few: "У вас {count} яблока"
  many: "У вас {count} яблок"
  other: "У вас {count} яблок"
```

Имя файла (без расширения) используется как код языка.

#### Получение переводов

Основной метод – `t`:

```python
# Простой перевод с подстановкой
result = i18n.t("hello", lang="en", name="World")
# "Hello, World!"

# Обращение к вложенному ключу
result = i18n.t("nested.key", lang="en")
# "Nested value"

# Плюрализация (автоматический выбор формы по count)
result = i18n.t("plural", lang="en", count=1)
# "You have 1 apple"
result = i18n.t("plural", lang="en", count=5)
# "You have 5 apples"

# Использование текущего языка (если свойство current_lang установлено)
i18n.current_lang = "ru"
result = i18n.t("hello", name="Мир")
# "Привет, Мир!"
```

**Параметры метода `t`**:

- `key` – строка пути к переводу (например, `"nested.key"`).
- `lang` – код языка. Если не указан, используется значение свойства `current_lang` (если установлен язык, иначе выдаст исключение).
- `fallback` – строка, которая возвращается, если перевод не найден (имеет приоритет над `strict`). Может содержать плейсхолдеры `{...}`.
- `strict` – булево значение:
  - `False` (по умолчанию) – при отсутствии перевода возвращается строка ошибки вида `"lang:key"`.
  - `True` – вызывается исключение `KeyError` с информативным сообщением.
- `**kwargs` – аргументы для подстановки в строку перевода (например, `name`, `count`).

#### Свойство `current_lang`

Позволяет установить текущий язык, который будет использоваться в последующих вызовах `t` без явного указания `lang`.

```python
i18n.current_lang = "en"
print(i18n.current_lang)  # "en"

# Установка несуществующего языка вызывает KeyError
i18n.current_lang = "fr"  # KeyError: Language not found: fr
```

#### Обработка ошибок и fallback

- Если язык не найден в загруженных словарях, модуль выполняет повторное сканирование директории (если с момента последнего сканирования прошло больше `scan_ttl` секунд).
- Если язык всё ещё не найден, поведение зависит от параметров `strict` и `fallback`:
  - Если передан `fallback`, возвращается его значение (с подстановкой аргументов).
  - Если `strict=False`, возвращается строка ошибки `"Language not found: <lang>"` (для отсутствующего языка) или `"<lang>:<key>"` (для отсутствующего ключа).
  - Если `strict=True`, вызывается `KeyError`.

Примеры:

```python
# Язык отсутствует, strict=False (по умолчанию)
i18n.t("hello", lang="de")  # "Language not found: de"

# Ключ отсутствует, strict=False
i18n.t("missing.key", lang="en")  # "en:missing.key"

# Использование fallback
i18n.t("hello", lang="de", fallback="Default greeting")  # "Default greeting"
i18n.t("hello", lang="de", fallback="Hello, {name}!", name="World")  # "Hello, World!"

# strict=True вызывает исключение
i18n.t("missing.key", lang="en", strict=True)  # KeyError: Translation not found: en:missing.key
```

#### Плюрализация

Модуль автоматически выбирает правильную форму множественного числа на основе правил CLDR. Для этого значение перевода должно быть словарём, ключи которого соответствуют плюральным формам (`one`, `few`, `many`, `other` и др.). Форма определяется по параметру `count`.

Правила плюрализации соответствуют [CLDR_48](https://github.com/unicode-org/cldr/releases/tag/release-48) (или берутся из кастомного файла переданного в параметре `plural_rules_path`). Файл должен содержать объект, где ключи – коды языков, а значения – словари с правилами CLDR (в формате, совместимом с библиотекой `babel.plural`).

#### Кастомные валидаторы (Появится в будущих обновлениях)

Валидаторы позволяют отфильтровать некорректные файлы переводов. Валидатор – это функция, принимающая загруженные данные и путь к файлу и возвращающая `True` (файл принимается) или `False` (файл игнорируется).

```python
def validator(data: dict, file: Path) -> bool:
    # Например, требовать наличие ключа "version"
    return "version" in data

# Валидаторы передаются при первом вызове конструктора I18n
i18n = I18n(Path("locales"), custom_validators=[validator])
```

#### Игнорируемые файлы

При сканировании директории игнорируются:
- Файлы с неподдерживаемым расширением (выводится предупреждение в лог).
- Файлы, чьё имя (без расширения) совпадает с именем файла правил плюрализации (например, `plurals.json`).
- Элементы, не являющиеся обычными файлами (символьные ссылки, директории и т.п.).

#### Пример полного использования

```python
from magutils.i18n import I18n
from pathlib import Path

# Инициализация (синглтон)
i18n = I18n(Path("locales"))

# Установка текущего языка
i18n.current_lang = "en"

# Получение переводов
print(i18n.t("hello", name="Alice"))                # Hello, Alice!
print(i18n.t("nested.key"))                         # Nested value
print(i18n.t("plural", count=3))                    # You have 3 apples

# Смена языка
i18n.current_lang = "ru"
print(i18n.t("hello", name="Алиса"))                # Привет, Алиса!
print(i18n.t("plural", count=2))                    # У вас 2 яблока

# Обработка отсутствующих ключей
print(i18n.t("unknown", fallback="Запасной текст")) # Запасной текст
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

### utils.env

Модуль для работы с переменными окружения, включая валидацию, загрузку из `.env` файлов, YAML конфигураций и интеграцию с Kubernetes. Основан на декораторе `environ` и функции `field`.

#### Основные компоненты

- **Декоратор `environ`** – оборачивает класс, превращая его в синглтон с автоматической загрузкой переменных окружения.
- **Функция `field`** – определяет поле конфигурации с возможностью указания значения по умолчанию, фабрики значений, алиасов.
- **Расширение `yaml`** – предоставляет фабрику для загрузки значений из YAML файлов.
- **Расширение `k8s`** – интеграция с Kubernetes Secrets (опционально).

#### Использование

Базовый пример:

```python
from magutils.env import environ, field

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
from magutils.env import environ, field
from magutils.env.ext.yaml_ import yaml

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
from magutils.env import environ, field
from magutils.env.ext.k8s import k8s_secret

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

### utils.jwt

Модуль для работы с JSON Web Tokens (JWT) – кодирование, декодирование и проверка подписи с использованием алгоритма HMAC-SHA256. Поддерживает автоматическую загрузку секрета из переменной окружения `JWT_SECRET`.

#### Основные функции

- `jwt_encode(payload: dict, secret: str = None, headers: dict = None) -> str` – кодирует payload в JWT токен.
- `jwt_decode(token: str, secret: str = None) -> DecodeResult` – декодирует и проверяет JWT токен, возвращает словарь с заголовками, payload и подписью.

#### Класс Config

Метакласс `Config` управляет конфигурацией по умолчанию:
- `secret` – секрет для подписи, загружается из `JWT_SECRET` или вызывает `KeyError` если обратиться к нему без предварительной установки, или переменной окружения.
- `default_header` – заголовок по умолчанию (`{"alg": "HS256", "typ": "JWT"}`).
- `precomp_header` – предвычисленный base64 заголовка (кэшируется).
- `hmac(secret)` – возвращает HMAC объект для подписи.

#### Пример использования

```python
import os
os.environ['JWT_SECRET'] = 'supersecret'

from magutils.jwt import jwt_encode, jwt_decode

payload = {"user_id": 42, "exp": 1672531200}
token = jwt_encode(payload)
print(token)  # eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo0MiwiZXhwIjoxNjcyNTMxMjAwfQ...

decoded = jwt_decode(token)
print(decoded['payload'])  # {'user_id': 42, 'exp': 1672531200}
```

#### Обработка ошибок

- `KeyError` – если секрет не задан в окружении и не передан явно.
- `ValueError` – при неверной подписи, истёкшем токене или некорректном формате.

### utils.starlark

Модуль для асинхронного выполнения скриптов на языке Starlark (подмножество Python) в изолированном контексте. Позволяет безопасно выполнять пользовательские скрипты с доступом к ограниченному набору функций (regex, время, JSON, вывод).

#### Основные классы

- `StarResult` – результат выполнения скрипта, со следующими полями:
    -  `success`: `bool` - был ли запуск успешен
    - `result`: `list|dict` - результат работы скрипта, если скрипт ничего не вернул, `result` будет содержать пустой `dict`
    - `prints`: `list[str]` - отладочный вывод, содержит список строк переданных в функцию `print` во время исполнения скрипта
    - `error`: `Exception` в случае возникновения ошибки, содержит экземпляр этой ошибки
- `Runner` – основной класс для выполнения скриптов

#### Функции и методы

- `Runner.run(script: str, data, wraper: str = None) -> Awaitable[StarResult]` – асинхронно выполняет скрипт с входными данными.
- `Runner.inst(wraper: str = None) -> Runner` – возвращает синглтон-инстанс Runner для заданного wrapper'а.
- `StarResult.result` – свойство, возвращающее результат или выбрасывающее исключение при ошибке.

#### Встроенные функции в рантайме Starlark

В скриптах доступны следующие функции и структуры:

- `print(*msgs)` – вывод сообщений (сохраняется в `StarResult.prints`).
- `re` – структура с методами:
  - `re.findall(pattern, text)` – аналог `re.findall` в Python.
  - `re.search(pattern, text, group=0)` – поиск первого совпадения regex.
- `time` – структура с методами времени:
  - `time.now()` – текущее время в секундах с эпохи.
  - `time.start` – переменная с временем старта скрипта в секундах.
  - `time.elapsed()` - время прошедшее с начала выполнения скрипта в секундах.
  - `time.sleep(...)` - аналог `time.sleep(...)` в python. Не влияет на асинхронный цикл вызвавший starlark.
- `json.encode(obj)`, `json.decode(str)` – работа с JSON строками внутри starlark скрипта.

#### Wrapper по умолчанию

Скрипт автоматически оборачивается в шаблон, который определяет функцию `process(input)` и возвращает результат в виде словаря или списка. Если результат не dict/list, он упаковывается в `{'result': ...}`. Пустой результат преобразуется в `{}`. Также wrapper предоставляет структуры `re` и `time` для доступа к regex и времени.

#### Пример использования

```python
import asyncio
from magutils.star import Runner

async def main():
    script = """
print("Processing input")
match = re.search(r'\\d+', input['text'])
return {'match': match}
"""
    data = {'text': 'abc123def'}
    result = await Runner.run(script, data)
    if result.success:
        print(result.result)      # {'match': '123'}
        print(result.prints)      # ['Processing input']
    else:
        print(result.error)       # исключение

asyncio.run(main())
```

#### Установка зависимостей

Модуль требует установки `starlark-pyo3`:

```bash
uv add starlark-pyo3
```

При импорте, если библиотека отсутствует, будет выброшено `ImportError` с подсказкой.

### utils.fsm

Лёгковесный модуль для хранения состояний и вызова коллбэков при переходах между ними. Это не полноценная FSM с построением графа состояний, валидацией переходов и т.д., а минималистичная группа состояний с низким оверхедом.

#### Основные компоненты

- **`State`** – класс, представляющий отдельное состояние с возможностью регистрации коллбэков на вход, выход и прогресс.
- **`StateGroup[T]`** – группа состояний, объединяющая несколько `State` в одну логическую единицу с возможностью переходов между ними.
- **`StateEvent`**, **`GroupEvent`**, **`TransitionEvent`** – события, передаваемые в коллбэки.
- **`StateError`** – исключение для ошибок, связанных с состояниями.

#### Создание состояний

```python
from magutils.fsm import State, StateGroup

class MyFSM(StateGroup):
    # Объявляем состояния как атрибуты класса
    init = State("init", start=True)          # стартовое состояние
    processing = State("processing")
    done = State("done", final=True)          # финальное состояние
```

#### Коллбэки состояний

Каждое состояние может иметь коллбэки на вход (`on_enter`), выход (`on_exit`) и прогресс (`on_progress`). Коллбэки – асинхронные функции, принимающие `StateEvent`.

```python
@MyFSM.init.on_exit
async def handle_exit_init(event):
    print(f"Exiting {event.state.name}")

@MyFSM.processing.on_enter
async def handle_enter_processing(event):
    print(f"Entering {event.state.name}")
    # event.model содержит привязанную модель (если есть)
```

#### Коллбэки группы

Группа может иметь коллбэки на старт (`on_start`), завершение (`on_finish`) и переход между состояниями (`on_transition`). Завершение вызывается при переходе в финальное состояние. Коллбэк перехода вызывается перед изменением состояния (но после проверок) и получает информацию об исходном и целевом состояниях.

```python
@MyFSM.on_start
async def handle_start(event):
    print(f"FSM {event.group.id} started")

@MyFSM.on_finish
async def handle_finish(event):
    print(f"FSM {event.group.id} finished")

@MyFSM.on_transition
async def handle_transition(event):
    print(f"Transition from {event.from_state.name} to {event.to_state.name}")
    # event.model содержит привязанную модель (если есть)
```

#### Работа с экземпляром

```python
# Создание экземпляра
fsm = MyFSM(id="my-fsm-1")

# Синхронный переход (запускает асинхронный коллбэк в фоне)
fsm.emit_nowait("processing")

# Асинхронный переход с ожиданием коллбэков
await fsm.emit("done")

# Текущее состояние
print(fsm.current_state.name)  # "done"
```

#### Привязка модели данных

`StateGroup` поддерживает типизацию через дженерик `StateGroup[MyModel]`, где `MyModel` – класс `pydantic.BaseModel`. Модель передаётся в конструктор и доступна в коллбэках через `event.model`.

```python
from pydantic import BaseModel

class Order(BaseModel):
    id: str
    amount: float

class OrderFSM(StateGroup[Order]):
    created = State("created", start=True)
    paid = State("paid")

order = Order(id="123", amount=99.99)
fsm = OrderFSM(model=order)

@OrderFSM.paid.on_enter
async def on_paid(event):
    # Модель автоматически передаётся
    print(f"Order {event.model.id} paid")
```

#### Сериализация и восстановление

Группа может быть сериализована в словарь (`dump`) и восстановлена (`load`). Сериализуются идентификатор, текущее состояние и модель (если она является pydantic моделью).

```python
# Дамп
packed = await fsm.dump()
# {
#     'name': 'OrderFSM',
#     'id': '...',
#     'current_state': 'paid',
#     'model': {'path': '...', 'data': {...}}
# }

# Загрузка
restored = OrderFSM.load(packed)
```

#### Обработка ошибок

- `StateError` выбрасывается при попытке перехода в несуществующее состояние, из финального состояния, при дублировании имён и т.п.
- Коллбэки, выбрасывающие исключения, логируются, но не прерывают работу FSM.

#### Особенности

- **Минимальный оверхед**: нет сложной валидации графа переходов.
- **Асинхронность**: все коллбэки асинхронные, выполняются через `BgTask`.
- **Потокобезопасность**: переходы защищены `asyncio.Lock`.
- **Типизация**: полная поддержка типов через дженерики.

#### Пример полного цикла

```python
import asyncio
from magutils.fsm import State, StateGroup
from pydantic import BaseModel

class TaskModel(BaseModel):
    title: str
    progress: int = 0

class TaskFSM(StateGroup[TaskModel]):
    todo = State("todo", start=True)
    in_progress = State("in_progress")
    done = State("done", final=True)

@TaskFSM.todo.on_exit
async def log_exit_todo(event):
    print(f"Task '{event.model.title}' left TODO")

@TaskFSM.in_progress.on_enter
async def start_work(event):
    event.model.progress = 50
    print(f"Task '{event.model.title}' in progress")

async def main():
    task = TaskModel(title="Implement FSM")
    fsm = TaskFSM(model=task)
    
    await fsm.emit("in_progress")
    await fsm.emit("done")
    
    print(f"Final progress: {fsm.model.progress}")  # 50

asyncio.run(main())
```

### utils.pipeline

Модуль для построения конвейеров обработки (pipeline) с декларативным описанием шагов. Поддерживает как асинхронные, так и синхронные шаги, а также onion-модель (middleware) через `yield`.

#### Основные компоненты

- **`Pipeline[T]`** – базовый класс конвейера. Наследуйтесь от него и помечайте методы-шаги декоратором `@step`.
- **`@step(order)`** – декоратор для пометки методов как шагов конвейера. `order` определяет порядок выполнения (меньше = раньше).
- **`PipeCTX`** – контекст выполнения с уникальным ID. Можно передать кастомную фабрику контекста через `ctx_factory`.
- **`PipeCTXFactory`** – протокол для создания кастомных контекстов.

#### Типы шагов

Декоратор `@step` автоматически определяет тип функции и выбирает соответствующую обёртку:

| Тип функции | Поведение |
|---|---|
| `async def` (без `yield`) | Асинхронный шаг. `return value` (не `None`) — ранний выход. `return None` / отсутствие `return` — переход к следующему шагу. |
| `def` (без `yield`) | Синхронный шаг. Аналогично: `return value` — ранний выход, иначе — переход дальше. |
| `async def` с `yield` | Асинхронный генератор. Код до `yield` выполняется на прямом пути, после `yield` — на обратном (onion-модель). |
| `def` с `yield` | Синхронный генератор. Аналогично: код до/после `yield` образует onion-слои. |

**Ранний выход:** если шаг возвращает не `None` (через `return value`) — результат сохраняется, и цепочка прерывается. Дальнейшие шаги не выполняются.

**Onion-модель через `yield`:** если шаг является генератором (содержит `yield`), код до `yield` выполняется при движении вглубь цепочки, а код после `yield` — при возврате обратно. Это позволяет реализовать логирование, замеры времени, транзакции и т.п.

#### Пример: асинхронные шаги

```python
import asyncio
from magutils.pipeline import Pipeline, step

class AuthPipeline(Pipeline):
    @step(order=1)
    async def validate(self):
        print("Step 1: validate")
        # return None — переход к следующему шагу

    @step(order=2)
    async def check_permissions(self):
        print("Step 2: check permissions")

    @step(order=3)
    async def process(self):
        print("Step 3: process")
        return {"status": "ok"}  # результат конвейера

async def main():
    result = await AuthPipeline.run()
    print(result.result)  # {"status": "ok"}

asyncio.run(main())
```

#### Пример: ранний выход

```python
class CachePipeline(Pipeline):
    @step(order=1)
    async def check_cache(self):
        # Если данные есть в кэше — ранний выход
        if cache_hit:
            return {"from": "cache", "data": "cached_value"}
        # return None — переход к следующему шагу

    @step(order=2)
    async def fetch_from_db(self):
        return {"from": "db", "data": "fresh_value"}

async def main():
    result = await CachePipeline.run()
    print(result.result)  # {"from": "cache", ...} или {"from": "db", ...}

asyncio.run(main())
```

#### Пример: onion-модель через yield

```python
class LoggingPipeline(Pipeline):
    @step(order=1)
    async def logger(self):
        print(f"[{self.step_name}] enter")
        yield  # точка переключения — следующий шаг
        print(f"[{self.step_name}] exit")

    @step(order=2)
    async def timer(self):
        import time
        start = time.time()
        yield  # следующий шаг
        elapsed = time.time() - start
        print(f"[{self.step_name}] took {elapsed:.3f}s")

    @step(order=3)
    async def handler(self):
        return {"result": "ok"}

async def main():
    result = await LoggingPipeline.run()
    print(result.result)  # {"result": "ok"}

asyncio.run(main())
# Вывод:
# [logger] enter
# [timer] enter
# [timer] took 0.000s
# [logger] exit
```

#### Пример: синхронные шаги

```python
class SyncPipeline(Pipeline):
    @step(order=1)
    def step_one(self):
        print("Sync step 1")

    @step(order=2)
    def step_two(self):
        print("Sync step 2")
        return {"done": True}

async def main():
    result = await SyncPipeline.run()
    print(result.result)  # {"done": True}

asyncio.run(main())
```

#### Кастомный контекст

```python
from magutils.pipeline import Pipeline, step, PipeCTX

class CustomCTX(PipeCTX):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_id = kwargs.get("user_id")

class UserPipeline(Pipeline):
    @step(order=1)
    async def greet(self):
        print(f"Hello user {self.ctx.user_id}")

async def main():
    result = await UserPipeline.run(ctx_factory=CustomCTX, user_id=42)
    # Выведет: Hello user 42

asyncio.run(main())
```

#### Особенности

- **Авто-регистрация шагов**: достаточно пометить метод декоратором `@step(n)` — он автоматически попадёт в конвейер.
- **4 типа шагов**: асинхронные, синхронные, асинхронные генераторы, синхронные генераторы — декоратор определяет тип автоматически.
- **Onion-модель**: `yield` в шаге-генераторе создаёт точку переключения контекста — код до `yield` выполняется на прямом пути, после `yield` — на обратном.
- **Ранний выход**: `return value` (не `None`) в любом шаге завершает конвейер, результат сохраняется в `self.result`.
- **Контекст выполнения**: каждый запуск конвейера получает уникальный ID через `PipeCTX`.
- **Типизация**: `Pipeline[T]` поддерживает дженерики для типизации результата.

## Лицензия

Проект распространяется под лицензией MIT. Подробнее см. файл LICENSE.
