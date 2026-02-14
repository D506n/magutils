import os
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.utils.time_utils import (
    format_time,
    from_timestamp,
    get_current_time,
    get_delta,
    get_tz,
    parse_time,
    seconds_stringify,
)


class TestTimeUtils:
    def test_get_tz_default(self):
        """Проверка получения часового пояса по умолчанию."""
        tz = get_tz()
        get_tz.cache_clear()  # следующий тест упадёт из-за кэша
        assert str(tz) == "UTC"

    @patch.dict(os.environ, {"TIMEZONE": "America/New_York"})
    def test_get_tz_custom(self):
        """Проверка получения кастомного часового пояса."""
        tz = get_tz()
        assert str(tz) == "America/New_York"

    def test_get_current_time(self):
        """Проверка, что текущее время в правильном часовом поясе."""
        current_time = get_current_time()
        assert isinstance(current_time, datetime)
        assert current_time.tzinfo is not None

    @patch.dict(os.environ, {"TIME_FORMAT": "%d.%m.%Y %H:%M"})
    def test_parse_time_custom_format_env(self):
        """Парсинг времени с форматом из переменной окружения."""
        dt = parse_time("01.01.2023 12:30")
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30

    def test_parse_time_explicit_format(self):
        """Парсинг с явно заданным форматом."""
        dt = parse_time("2023-12-25T10:15:30.123456+0300", "%Y-%m-%dT%H:%M:%S.%f%z") # noqa
        assert dt.year == 2023
        assert dt.month == 12
        assert dt.day == 25
        assert dt.tzinfo is not None
        assert dt.tzinfo.utcoffset(None).total_seconds() == 10800

    @patch.dict(os.environ, {"TIME_FORMAT": "%Y-%m-%d"})
    def test_format_time_custom_format_env(self):
        """Форматирование времени с форматом из переменной окружения."""
        dt = datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        result = format_time(dt)
        assert result == "2023-12-31"

    def test_format_time_explicit_format(self):
        """Форматирование с явным форматом."""
        dt = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = format_time(dt, "%d/%m/%Y")
        assert result == "01/01/2023"

    def test_get_delta_now(self):
        """Разница между двумя датами (сейчас и заданная)."""
        past = datetime(2023, 1, 1, tzinfo=timezone.utc)
        with patch("src.utils.time_utils.get_current_time") as mock_now:
            mock_now.return_value = datetime(2023, 1, 2, tzinfo=timezone.utc)
            delta = get_delta(past)
            assert delta.days == 1

    def test_get_delta_two_dates(self):
        """Разница между двумя заданными датами."""
        dt1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2023, 1, 3, tzinfo=timezone.utc)
        delta = get_delta(dt1, dt2)
        assert delta.days == 2

    @pytest.mark.parametrize(
        "seconds, expected",
        [
            (0, "0 m."),
            (30, "0 m."),
            (59, "0 m."),
            (60, "1 m."),
            (119, "1 m."),
            (120, "2 m."),
            (3599, "59 m."),
            (3600, "1 h."),
            (3660, "1 h. 1 m."),
            (7199, "1 h. 59 m."),
            (7200, "2 h."),
            (7265, "2 h. 1 m."),
            (3600 * 5 + 60 * 3, "5 h. 3 m."),
            (3600 * 25 + 60 * 10, "25 h. 10 m."),
        ],
    )
    def test_valid_seconds(self, seconds, expected):
        """Тест корректных (неотрицательных) значений."""
        assert seconds_stringify(seconds) == expected

    def test_negative_seconds_raises_error(self):
        """Отрицательные секунды вызывают ValueError."""
        with pytest.raises(ValueError, match="Seconds must be non-negative"):
            seconds_stringify(-1)

        with pytest.raises(ValueError, match="Seconds must be non-negative"):
            seconds_stringify(-100)

    # @patch.dict(os.environ, {'TIMEZONE': "Europe/Moscow"})
    def test_from_timestamp(self):
        """Проверка преобразования timestamp в datetime."""
        get_tz.cache_clear()  # сброс кэша таймзоны
        dt = datetime(1970, 1, 1, 0, tzinfo=get_tz())
        assert from_timestamp(0) == dt

        dt = datetime(2026, 2, 7, 15, 34, 3, tzinfo=get_tz())
        assert from_timestamp(1770478443) == dt

        dt = get_current_time()
        dt = dt.replace(microsecond=0)
        t = time.time()
        dt2 = from_timestamp(t)
        dt2 = dt2.replace(microsecond=0)
        assert dt == dt2