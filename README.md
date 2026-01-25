## D506n's python app template

Набор готовых функций и классов для создания приложений на Python.

## Использование шаблона

`Linux`
```bash
git clone https://github.com/D506n/pyapp_template.git.
rm -rf .git
git init
git add .
git commit -m "Initial commit"
uv venv
source .venv/bin/activate
uv sync
```

`Windows`
```powershell
git clone https://github.com/D506n/pyapp_template.git
cd pyapp_template
Remove-Item -Recurse -Force .git
git init
git add .
git commit -m "Initial commit"
uv venv
.venv\Scripts\activate
uv sync
```

## Для доработки шаблона

`Linux`
```bash
git clone https://github.com/D506n/pyapp_template.git.
uv venv
source .venv/bin/activate
uv sync
```

`Windows`
```powershell
git clone https://github.com/D506n/pyapp_template.git.
uv venv
.venv\Scripts\activate
uv sync
```

## Документация:

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
  - [env](#utilsenv)
  - [id](#utilsid)
  - [json_path](#utilsjson_path)
  - [singleton](#utilssingleton)
  - [time_utils](#utilstime_utils)

### logging

### logging.config

### logging.formatters

### logging.formatters.coloredconsole

### logging.formatters.monocolor

### logging.formatters.json

### logging.handlers

### logging.handlers.asyncconsolehandler

### logging.handlers.asyncfilehandler

### utils

### utils.env

### utils.id

`def gen_id(alphabet: str = DEFAULT_ALPHABET, size: int = 15)`

Функция для генерации строк ID работает на основе алгоритма NanoID. Стандартный алфавит: `abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789`
Такие ID остаются весьма уникальными, при более короткой строке чем uuid4. Калькулятор уникальности: https://zelark.github.io/nano-id-cc/
С параметрами которые выставлены в функции по умолчанию, для вероятности коллизии 1% нужно сгенерировать 3 триллиона ID.

Пример:

```python
from src.utils.id import gen_id

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

Модуль для доступа к объектам в словарях и списках по строковому пути.

`Синтаксис путей`

Для манипуляций с json подобным объектом путь к аттрибуту должен строиться по следующим правилам:

- Фрагменты пути разделяются точкой
- Для доступа к полю по имени, достаточно просто указать в строке имя нужного поля
- Для доступа к элементам словаря указываются целые числа, индексы нужных элементов
- Для доступа к последнему элементу словаря указывается -1
- При добавлении новых элементов в объект, можно явно указать что в список нужно добавить новый элемент, для этого используется ключ !append

Более подробное описание работы модуля см. в описании функций.

`def get_by_path(obj: dict | list, path: str)`

Функция для получения элементов из объекта по пути.

Пример:

```python
from src.utils.json_path import get_by_path

some_data = {
    'a': {
        'b': {
            'c': 1
        }
    }, 
    'some': [
        1, 
        2, 
        3
    ], 
    'another': {
        'field': 'value'
    }
}

print(get_by_path(some_data, 'a.b.c'))
# >>> 1
print(get_by_path(some_data, 'some.1'))
# >>> 2
print(get_by_path(some_data, 'some.-1'))
# >>> 3
print(get_by_path(some_data, 'another.field'))
# >>> value
print(get_by_path(some_data, 'another.nonexistent'))
# >>> KeyError: 'Key 'nonexistent' not found in {'field': 'value'}'
```

`def set_by_path(obj, path: str, value)`

Функция для добавления/замены полей в словаре/списке по указанному пути.

При добавлении поля которого ещё нет в объекте, функция будет пытаться автоматически создавать новые слои на основе того, какие элементы пути нужно добавить(подробнее в примере).

Пример:

```python
from src.utils.json_path import set_by_path

some_data = {
    'a': {
        'b': {
            'c': 1
        }
    }, 
    'some': [
        1, 
        2, 
        3
    ], 
    'another': {
        'field': 'value'
    }
}

set_by_path(some_data, 'a.b.c', 2)
print(some_data['a']['b']['c'])
# >>> 2

set_by_path(some_data, 'some.0', 4)
print(some_data['some'])
# >>> [4, 2, 3]
set_by_path(some_data, 'some.!append', 5)
print(some_data['some'])
# >>> [4, 2, 3, 5]

set_by_path(some_data, 'another.new_layer.key', 'new_value') # добавление нового словаря по ключу new_layer с полем key
print(some_data['another']['new_layer'])
# >>> {'key': 'new_value'}

print(some_data['another'])
# >>> {'field': 'value', 'new_layer': {'key': 'new_value'}}
```

`def format(template: str, data: dict):`

Форматирует строку вида `'Строка содержащая {шаблонные.вставки.с.путями}'` подставляя значения из словаря/списка по указанным в шаблоне путям.

Пример:

```python
from src.utils.import format

some_data = {
    'a': {
        'b': {
            'c': 1
        }
    }, 
    'some': [
        1, 
        2, 
        3
    ], 
    'another': {
        'field': 'value'
    }
}

print(format('a.b.c: {a.b.c}, some: {some}, another.field: {another.field}', some_data))
# >>> a.b.c: 1, some: [1, 2, 3], another.field: value
```

### utils.singleton

`def singleton(cls)`

Декоратор который делает декорируемый класс синглтоном.

Пример:

```python
from src.utils.singleton import singleton

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
