from src.magutils.singleton import singleton


class TestSingleton:
    """Тесты для декоратора @singleton."""

    def test_singleton_returns_same_instance(self):
        """Один и тот же экземпляр возвращается при повторных вызовах."""
        @singleton
        class TestClass:
            pass

        instance1 = TestClass()
        instance2 = TestClass()

        assert instance1 is instance2

    def test_init_called_only_once(self):
        """Метод __init__ вызывается только при первом создании."""
        @singleton
        class TestClass:
            def __init__(self):
                self.init_count = getattr(self, 'init_count', 0) + 1

        instance1 = TestClass()
        instance2 = TestClass()

        assert instance1.init_count == 1
        assert instance2.init_count == 1
        assert instance1 is instance2

    def test_singleton_with_args(self):
        """Аргументы передаются только при первом вызове."""
        @singleton
        class TestClass:
            def __init__(self, value):
                self.value = value

        instance1 = TestClass("first")
        instance2 = TestClass("second")

        assert instance1.value == "first"
        assert instance2.value == "first"
        assert instance1 is instance2

    def test_singleton_with_kwargs(self):
        """Именованные аргументы учитываются только при первом вызове."""
        @singleton
        class TestClass:
            def __init__(self, *, name):
                self.name = name

        instance1 = TestClass(name="Alice")
        instance2 = TestClass(name="Bob")

        assert instance1.name == "Alice"
        assert instance2.name == "Alice"
        assert instance1 is instance2

    def test_different_classes_do_not_interfere(self):
        """Разные классы не конфликтуют в кэше декоратора."""
        @singleton
        class ClassA:
            def __init__(self, x):
                self.x = x

        @singleton
        class ClassB:
            def __init__(self, y):
                self.y = y

        a1 = ClassA(1)
        b1 = ClassB(2)
        a2 = ClassA(3)
        b2 = ClassB(4)

        assert a1.x == 1
        assert a2.x == 1
        assert b1.y == 2
        assert b2.y == 2

        assert a1 is a2
        assert b1 is b2
        assert a1 is not b1

    def test_singleton_wraps_preserves_name(self):
        """Декоратор сохраняет имя класса."""
        @singleton
        class ServiceManager:
            pass

        assert ServiceManager.__name__ == "ServiceManager"

    def test_singleton_multiple_calls_with_none(self):
        """Проверка, что None — валидное значение, если оно возвращается."""
        @singleton
        class Nullable:
            def __init__(self):
                self.data = None

        instance1 = Nullable()
        instance2 = Nullable()

        assert instance1 is instance2
        assert instance1.data is None

    def test_mock_init_call_count(self):
        """Проверка, что __init__ вызывается ровно один раз."""

        num = [0]

        @singleton
        class TestClass:
            def __init__(self, num):
                num[0] += 1

        TestClass(num)
        TestClass(num)
        TestClass(num)
        assert num[0] == 1