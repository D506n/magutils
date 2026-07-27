import json
import shutil
import time
from pathlib import Path

import pytest
import yaml

from magutils.inter import _I18n, I18n


class TestI18n:
    """Тесты для класса I18n (синглтон) и базового класса _I18n."""

    @pytest.fixture
    def temp_locdir(self, tmp_path):
        """Создаёт временную директорию с тестовыми файлами переводов."""
        # Создаём JSON файл для языка 'en'
        en_file = tmp_path / 'en.json'
        en_data = {
            'hello': 'Hello, {name}!',
            'nested': {
                'key': 'Nested value'
            },
            'plural': {
                'one': 'You have {count} apple',
                'other': 'You have {count} apples'
            }
        }
        en_file.write_text(json.dumps(en_data), encoding='utf-8')

        # Создаём YAML файл для языка 'ru'
        ru_file = tmp_path / 'ru.yaml'
        ru_data = {
            'hello': 'Привет, {name}!',
            'nested': {
                'key': 'Вложенное значение'
            },
            'plural': {
                'one': 'У вас {count} яблоко',
                'few': 'У вас {count} яблока',
                'many': 'У вас {count} яблок',
                'other': 'У вас {count} яблок'
            }
        }
        ru_file.write_text(yaml.dump(ru_data, allow_unicode=True), encoding='utf-8')

        return tmp_path

    def test_init_with_valid_directory(self, temp_locdir):
        """Инициализация с корректной директорией."""
        i18n = _I18n(temp_locdir)
        assert i18n.locdir == temp_locdir
        assert 'en' in i18n.dictionaries
        assert 'ru' in i18n.dictionaries
        assert isinstance(i18n.pluralizers, dict)
        assert 'en' in i18n.pluralizers
        assert 'ru' in i18n.pluralizers
        assert i18n.current_lang == ''  # по умолчанию пустая строка

    def test_init_with_string_path(self, temp_locdir):
        """Инициализация с путём в виде строки."""
        i18n = _I18n(str(temp_locdir))
        assert i18n.locdir == temp_locdir

    def test_init_with_invalid_directory(self):
        """Инициализация с несуществующей директорией вызывает ошибку."""
        with pytest.raises(ValueError, match='Locdir must be directory!'):
            _I18n('/non/existent/path')

    def test_init_with_empty_locdir(self):
        """Инициализация с пустым locdir вызывает ValueError."""
        with pytest.raises(ValueError, match='Locdir must be provided for first call!'):
            _I18n('')
        with pytest.raises(ValueError, match='Locdir must be provided for first call!'):
            _I18n(locdir='')
        # Передача None также должна вызывать ошибку, так как not locdir будет True
        with pytest.raises(ValueError, match='Locdir must be provided for first call!'):
            _I18n(None)

    def test_init_with_file_path(self, temp_locdir):
        """Инициализация с путём к файлу (не директории) вызывает ошибку."""
        file_path = temp_locdir / 'en.json'
        with pytest.raises(ValueError, match='Locdir must be directory!'):
            _I18n(file_path)

    def test_init_with_no_translation_files(self, tmp_path):
        """Директория без файлов переводов вызывает FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _I18n(tmp_path)

    def test_init_with_custom_plural_rules(self, temp_locdir, tmp_path):
        """Использование кастомного файла правил плюрализации."""
        # Создаём отдельную директорию для переводов, чтобы не смешивать с файлом правил
        translations_dir = tmp_path / 'translations'
        translations_dir.mkdir()
        # Копируем файлы переводов из temp_locdir
        for f in temp_locdir.iterdir():
            if f.is_file():
                shutil.copy(f, translations_dir / f.name)
        # Создаём кастомные правила плюрализации в другом месте
        custom_rules = tmp_path / 'custom_plurals.json'
        # Формат, аналогичный стандартному plurals.json (упрощённый)
        rules = {
            'en': {
                'one': 'n = 1 @integer 1 @decimal 1.0, 1.00, 1.000, 1.0000',
                'other': ' @integer 0, 2~16, 100, 1000, 10000, 100000, 1000000, … @decimal 0.0~0.9, 1.1~1.6, 10.0, 100.0, 1000.0, 10000.0, 100000.0, 1000000.0, …'
            },
            'ru': {
                'one': 'n = 1 @integer 1 @decimal 1.0, 1.00, 1.000, 1.0000',
                'few': 'n % 10 = 2..4 and n % 100 != 12..14 @integer 2~4, 22~24, 32~34, 42~44, 52~54, 62, 102, 1002, … @decimal 2.0, 3.0, 4.0, 2.1, 3.1, 4.1, 2.2, 3.2, 4.2, …',
                'many': 'n % 10 = 0 or n % 10 = 5..9 or n % 100 = 11..14 @integer 0, 5~19, 100, 1000, 10000, 100000, 1000000, … @decimal 0.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, …',
                'other': ' @integer 1.0~1.9, 21.0, 31.0, 41.0, 51.0, 61.0, 71.0, 81.0, 101.0, 1001.0, …'
            }
        }
        custom_rules.write_text(json.dumps(rules), encoding='utf-8')
        i18n = _I18n(translations_dir, plural_rules_path=custom_rules)
        assert i18n.plural_rules_path == custom_rules

    def test_init_with_default_plural_rules(self, temp_locdir):
        """По умолчанию используется plurals.json из пакета."""
        i18n = _I18n(temp_locdir)
        expected_path = Path(__file__).parent.parent / 'src' / 'magutils' / 'plurals.json'
        assert i18n.plural_rules_path == expected_path

    def test_scan_dir_loads_files(self, temp_locdir):
        """Сканирование директории загружает файлы."""
        i18n = _I18n(temp_locdir)
        assert 'en' in i18n.dictionaries
        assert 'ru' in i18n.dictionaries
        # Проверяем, что данные загружены корректно
        result = i18n.t('hello', lang='en', name='World')
        assert result == 'Hello, World!'

    def test_scan_dir_ignores_unsupported_format(self, temp_locdir):
        """Файлы с неподдерживаемым расширением игнорируются."""
        unsupported = temp_locdir / 'de.txt'
        unsupported.write_text('hello: Hallo', encoding='utf-8')
        i18n = _I18n(temp_locdir)
        assert 'de' not in i18n.dictionaries

    def test_scan_dir_handles_bad_json(self, temp_locdir, caplog):
        """Некорректный JSON файл вызывает ошибку в логе и не загружается."""
        bad_json = temp_locdir / 'bad2.json'
        bad_json.write_text('{invalid json', encoding='utf-8')
        i18n = _I18n(temp_locdir)
        assert 'bad2' not in i18n.dictionaries
        # Проверяем, что ошибка залогирована
        assert any('parsing error' in message for message in caplog.messages)

    def test_scan_dir_handles_bad_yaml(self, temp_locdir, caplog):
        """Некорректный YAML файл вызывает ошибку в логе и не загружается."""
        bad_yaml = temp_locdir / 'bad2.yaml'
        bad_yaml.write_text('invalid: yaml: :', encoding='utf-8')
        i18n = _I18n(temp_locdir)
        assert 'bad2' not in i18n.dictionaries
        assert any('parsing error' in message for message in caplog.messages)

    def test_current_lang_property(self, temp_locdir):
        """Свойство current_lang можно установить и получить."""
        i18n = _I18n(temp_locdir)
        assert i18n.current_lang == ''
        i18n.current_lang = 'en'
        assert i18n.current_lang == 'en'
        # Установка несуществующего языка вызывает KeyError
        with pytest.raises(KeyError, match='Language not found: fr'):
            i18n.current_lang = 'fr'

    def test_t_simple_string(self, temp_locdir):
        """Перевод простой строки с подстановкой."""
        i18n = _I18n(temp_locdir)
        result = i18n.t('hello', lang='en', name='World')
        assert result == 'Hello, World!'

    def test_t_nested_key(self, temp_locdir):
        """Обращение к вложенному ключу."""
        i18n = _I18n(temp_locdir)
        result = i18n.t('nested.key', lang='en')
        assert result == 'Nested value'

    def test_t_missing_key_non_strict(self, temp_locdir):
        """Отсутствующий ключ в нестрогом режиме возвращает строку ошибки."""
        i18n = _I18n(temp_locdir)
        result = i18n.t('missing.key', lang='en', strict=False)
        print(result)

        assert result == 'en:missing.key'

    def test_t_missing_key_strict(self, temp_locdir):
        """Отсутствующий ключ в строгом режиме вызывает KeyError."""
        i18n = _I18n(temp_locdir)
        with pytest.raises(KeyError, match='Translation not found'):
            i18n.t('missing.key', lang='en', strict=True)

    def test_t_pluralization_english(self, temp_locdir):
        """Плюрализация для английского языка."""
        i18n = _I18n(temp_locdir)
        # one
        result = i18n.t('plural', lang='en', count=1)
        assert result == 'You have 1 apple'
        # other
        result = i18n.t('plural', lang='en', count=5)
        assert result == 'You have 5 apples'

    def test_t_pluralization_russian(self, temp_locdir):
        """Плюрализация для русского языка."""
        i18n = _I18n(temp_locdir)
        # one
        result = i18n.t('plural', lang='ru', count=1)
        assert result == 'У вас 1 яблоко'
        # few
        result = i18n.t('plural', lang='ru', count=2)
        assert result == 'У вас 2 яблока'
        result = i18n.t('plural', lang='ru', count=4)
        assert result == 'У вас 4 яблока'
        # many
        result = i18n.t('plural', lang='ru', count=5)
        assert result == 'У вас 5 яблок'
        result = i18n.t('plural', lang='ru', count=11)
        assert result == 'У вас 11 яблок'
        # other (для дробных?)
        result = i18n.t('plural', lang='ru', count=1.5)
        assert result == 'У вас 1.5 яблок'

    def test_t_pluralization_missing_plural_key(self, temp_locdir):
        """Если для плюральной формы нет ключа, возвращается ошибка."""
        i18n = _I18n(temp_locdir)
        # В английском есть только 'one' и 'other', нет 'few'
        result = i18n.t('plural', lang='en', count=2, strict=False)
        # Должен использовать 'other'
        assert result == 'You have 2 apples'

    def test_t_language_not_found_rescan(self, temp_locdir):
        """Если язык не найден, происходит повторное сканирование по истечении TTL."""
        i18n = _I18n(temp_locdir, scan_ttl=0.1)  # маленький TTL
        # Убедимся, что язык 'de' отсутствует
        assert 'de' not in i18n.dictionaries
        # Подождём больше TTL
        time.sleep(0.2)
        # Добавим новый файл после инициализации
        de_file = temp_locdir / 'de.json'
        de_file.write_text(json.dumps({'hello': 'Hallo'}), encoding='utf-8')
        # Вызов перевода с языком 'de' должен вызвать повторное сканирование
        result = i18n.t('hello', lang='de')
        # После сканирования 'de' должен появиться в словарях
        assert 'de' in i18n.dictionaries
        assert result == 'Hallo'

    def test_t_language_not_found_fallback(self, temp_locdir):
        """Если язык не найден и повторное сканирование не помогает, используется fallback."""
        i18n = _I18n(temp_locdir, scan_ttl=10.0)  # большой TTL, сканирование не произойдёт
        # Язык 'de' отсутствует, должен быть KeyError (strict=False по умолчанию)
        result = i18n.t('hello', lang='de', strict=False)
        print(result)
        assert result == 'Language not found: de'
        # С fallback должен вернуть fallback строку
        result = i18n.t('hello', lang='de', fallback='Default text')
        assert result == 'Default text'

    def test_t_fallback_parameter(self, temp_locdir):
        """Параметр fallback позволяет вернуть запасную строку вместо ошибки."""
        i18n = _I18n(temp_locdir)
        # Ключ отсутствует
        result = i18n.t('missing.key', lang='en', fallback='Default text')
        assert result == 'Default text'
        # Язык отсутствует
        result = i18n.t('hello', lang='de', fallback='Default text')
        assert result == 'Default text'
        # Fallback с подстановкой
        result = i18n.t('hello', lang='de', fallback='Hello, {name}!', name='World')
        assert result == 'Hello, World!'
        # Fallback имеет приоритет над strict
        result = i18n.t('missing.key', lang='en', strict=True, fallback='Default')
        assert result == 'Default'

    def test_t_strict_with_fallback(self, temp_locdir):
        """Параметр strict игнорируется, если передан fallback."""
        i18n = _I18n(temp_locdir)
        # strict=True, но есть fallback - должен вернуть fallback
        result = i18n.t('missing.key', lang='en', strict=True, fallback='Default')
        assert result == 'Default'

    def test_custom_validator(self, temp_locdir):
        """Кастомный валидатор проверяет загруженные данные."""
        def validator(data, file):
            return data.get('hello') is not None

        i18n = _I18n(temp_locdir, custom_validators=[validator])
        # Файлы должны пройти валидацию
        assert 'en' in i18n.dictionaries
        assert 'ru' in i18n.dictionaries

    # TODO: добавить валидаторы в будущем
    # def test_custom_validator_rejects(self, temp_locdir, tmp_path): 
    #     """Кастомный валидатор может отклонить файл."""
    #     def validator(data, file):
    #         return False  # отклоняем все

    #     # Создаём отдельную директорию с одним файлом
    #     test_dir = tmp_path / 'test'
    #     test_dir.mkdir()
    #     (test_dir / 'en.json').write_text(json.dumps({'hello': 'Hi'}), encoding='utf-8')
    #     with pytest.raises(FileNotFoundError):
    #         _I18n(test_dir, custom_validators=[validator])

    def test_singleton_behavior(self, temp_locdir):
        """I18n является синглтоном (декоратор @singleton)."""
        i18n1 = I18n(temp_locdir)
        i18n2 = I18n(temp_locdir)
        assert i18n1 is i18n2
        # Параметры инициализации игнорируются после первого вызова
        i18n3 = I18n(temp_locdir)
        assert i18n3 is i18n1

    def test_strict_mode_key_error_message(self, temp_locdir):
        """Сообщение об ошибке в строгом режиме содержит информацию о языке и ключе."""
        i18n = _I18n(temp_locdir)
        try:
            i18n.t('missing.key', lang='en', strict=True, count=5)
        except KeyError as e:
            assert 'Translation not found' in str(e)
            assert 'en:missing.key' in str(e)

    def test_scan_dir_non_dict_translation(self, temp_locdir, caplog):
        """Файл перевода, который парсится, но не является словарём, игнорируется."""
        # Создаём JSON файл, содержащий массив (не словарь)
        array_file = temp_locdir / 'array.json'
        array_file.write_text('["hello", "world"]', encoding='utf-8')
        i18n = _I18n(temp_locdir)
        # Язык 'array' не должен быть загружен
        assert 'array' not in i18n.dictionaries
        # Проверяем, что ошибка залогирована
        assert any('Incorrect translation file format' in message for message in caplog.messages)

    def test_scan_dir_skips_plural_rules_file(self, temp_locdir, tmp_path):
        """Файл с именем, совпадающим с файлом правил плюрализации, игнорируется."""
        # Создаём кастомный файл правил плюрализации в отдельной директории
        custom_rules = tmp_path / 'custom_plurals.json'
        custom_rules.write_text('{"en": {}, "ru": {}}', encoding='utf-8')
        # Создаём директорию переводов
        translations_dir = tmp_path / 'translations'
        translations_dir.mkdir()
        # Копируем файлы переводов из temp_locdir
        for f in temp_locdir.iterdir():
            if f.is_file():
                shutil.copy(f, translations_dir / f.name)
        # Создаём файл с именем, совпадающим с файлом правил плюрализации
        fake_rules = translations_dir / 'custom_plurals.json'
        fake_rules.write_text('{"hello": "Hello"}', encoding='utf-8')
        # Инициализируем I18n с кастомным файлом правил
        i18n = _I18n(translations_dir, plural_rules_path=custom_rules)
        # Файл 'custom_plurals' не должен быть загружен как перевод
        assert 'custom_plurals' not in i18n.dictionaries
        # Но стандартные переводы должны быть
        assert 'en' in i18n.dictionaries
        assert 'ru' in i18n.dictionaries

    def test_scan_dir_skips_subdirectory(self, temp_locdir):
        """Поддиректории игнорируются."""
        subdir = temp_locdir / 'sub'
        subdir.mkdir()
        # Создаём файл внутри поддиректории (не должен быть загружен)
        (subdir / 'de.json').write_text('{"hello": "Hallo"}', encoding='utf-8')
        i18n = _I18n(temp_locdir)
        # Язык 'de' не должен быть загружен
        assert 'de' not in i18n.dictionaries
        # Поддиректория не должна влиять на загрузку других файлов
        assert 'en' in i18n.dictionaries
        assert 'ru' in i18n.dictionaries

    def test_scan_dir_skips_non_file(self, temp_locdir):
        """Элементы директории, не являющиеся файлами (например, символьные ссылки), игнорируются."""
        import os
        # Создаём обычный файл, чтобы потом создать на него символьную ссылку
        target = temp_locdir / 'target.json'
        target.write_text('{"hello": "Hello"}', encoding='utf-8')
        # Создаём символьную ссылку с расширением .json
        symlink = temp_locdir / 'symlink.json'
        symlink.symlink_to(target)
        # Убедимся, что symlink.is_file() возвращает True (символьная ссылка на файл считается файлом)
        # Поэтому нужно удалить целевой файл, чтобы symlink стал битой ссылкой и is_file() вернул False
        target.unlink()
        # Теперь symlink.is_file() должно быть False
        assert not symlink.is_file()
        i18n = _I18n(temp_locdir)
        # Язык 'symlink' не должен быть загружен
        assert 'symlink' not in i18n.dictionaries
        # Остальные переводы должны быть загружены
        assert 'en' in i18n.dictionaries
        assert 'ru' in i18n.dictionaries

    def test_scan_dir_missing_plural_rules(self, tmp_path):
        """Отсутствие правил плюрализации для языка вызывает ValueError."""
        # Создаём кастомный файл правил плюрализации только с 'en'
        custom_rules = tmp_path / 'custom_plurals.json'
        custom_rules.write_text('{"en": {}}', encoding='utf-8')
        # Создаём директорию переводов
        translations_dir = tmp_path / 'translations'
        translations_dir.mkdir()
        # Создаём файл перевода для языка 'en' (есть в правилах)
        en_file = translations_dir / 'en.json'
        en_file.write_text('{"hello": "Hello"}', encoding='utf-8')
        # Создаём файл перевода для языка 'fr' (нет в правилах)
        fr_file = translations_dir / 'fr.json'
        fr_file.write_text('{"hello": "Bonjour"}', encoding='utf-8')
        # Инициализация должна вызвать ValueError, потому что для 'fr' нет правил
        with pytest.raises(ValueError, match='Plural rules not found for language: fr'):
            _I18n(translations_dir, plural_rules_path=custom_rules)

    def test_scan_dir_plural_rules_not_dict(self, tmp_path):
        """Правило плюрализации не словарь вызывает ValueError."""
        # Создаём кастомный файл правил, где значение для 'en' - строка (не словарь)
        custom_rules = tmp_path / 'bad_rules.json'
        custom_rules.write_text('{"en": "not a dict"}', encoding='utf-8')
        # Создаём директорию переводов
        translations_dir = tmp_path / 'translations'
        translations_dir.mkdir()
        # Создаём файл перевода для языка 'en' (чтобы он был загружен)
        en_file = translations_dir / 'en.json'
        en_file.write_text('{"hello": "Hello"}', encoding='utf-8')
        # Инициализация должна вызвать ValueError, потому что правило для 'en' не словарь
        with pytest.raises(ValueError, match='Plural rules must be a dictionary'):
            _I18n(translations_dir, plural_rules_path=custom_rules)

    def test_t_non_string_non_dict_value(self, temp_locdir):
        """Значение перевода не строка и не словарь вызывает KeyError."""
        # Модифицируем временный файл перевода, добавив число
        en_file = temp_locdir / 'en.json'
        data = json.loads(en_file.read_text())
        data['number'] = 42  # число, не строка и не словарь
        en_file.write_text(json.dumps(data), encoding='utf-8')
        i18n = _I18n(temp_locdir)
        # В нестрогом режиме должен вернуться ключ ошибки
        result = i18n.t('number', lang='en', strict=False)
        assert result == 'en:number'
        # В строгом режиме должно быть KeyError
        with pytest.raises(KeyError, match='en:number'):
            i18n.t('number', lang='en', strict=True)

    def test_t_plural_key_not_found(self, temp_locdir):
        """Плюральная форма не найдена в словаре вызывает KeyError."""
        # Модифицируем временный файл перевода, добавив словарь плюральных форм без нужной формы
        en_file = temp_locdir / 'en.json'
        data = json.loads(en_file.read_text())
        # Оставляем только 'one', удаляем 'other'
        data['plural'] = {'one': 'You have {count} apple'}
        en_file.write_text(json.dumps(data), encoding='utf-8')
        i18n = _I18n(temp_locdir)
        # Для count=5 (форма 'other') должна быть ошибка
        result = i18n.t('plural', lang='en', count=5, strict=False)
        # Ожидаем строку ошибки с информацией о плюральной форме
        assert 'en:plural' in result
        assert 'other' in result
        # В строгом режиме должно быть KeyError
        with pytest.raises(KeyError, match='en:plural'):
            i18n.t('plural', lang='en', count=5, strict=True)