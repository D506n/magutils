from string import ascii_letters, digits

import pytest

from src.magutils.id import Config, gen_id, is_valid


class TestId:
    def test_gen_id_default(self):
        i = gen_id()
        assert len(i) == 15
        assert set(i).issubset(set(ascii_letters + digits))

    @pytest.mark.parametrize(
        "size, alphabet",
        [
            (15, ascii_letters),
            (10, digits),
            (25, ascii_letters + digits),
        ],
    )
    def test_gen_id_custom(self, size, alphabet):
        Config.size = size
        Config.alphabet = alphabet
        i = gen_id()
        assert len(i) == size
        assert set(i).issubset(set(alphabet))

    def test_config_setters(self):
        with pytest.raises(ValueError, match='The id size cannot be shorter than 5 characters.'):  # noqa
            Config.size = 0
        with pytest.raises(ValueError, match='The alphabet cannot be empty.'):
            Config.alphabet = ''
        with pytest.raises(ValueError, match='Characters in the alphabet must be unique.'): # noqa
            Config.alphabet = 'abcabcabcabcabc'
        with pytest.raises(ValueError, match='The alphabet must contain at least 10 characters.'): # noqa
            Config.alphabet = 'abc'

    def test_is_valid(self):
        Config.size = 15
        Config.alphabet = ascii_letters + digits
        assert is_valid(gen_id())
        with pytest.raises(ValueError, match='ID is too short'):
            is_valid('')
        with pytest.raises(ValueError, match='ID is too long'):
            is_valid('a' * 100)
        with pytest.raises(ValueError, match='Invalid id'):
            is_valid('1234567890!@#$%')


class TestGenIdCustomParams:
    """Параметры gen_id переопределяют глобальный Config без его изменения."""

    def setup_method(self):
        Config.size = 15
        Config.alphabet = ascii_letters + digits

    def test_custom_size_only(self):
        i = gen_id(size=10)
        assert len(i) == 10
        assert set(i).issubset(set(ascii_letters + digits))

    def test_custom_alphabet_only(self):
        alpha = '0123456789ABCDEF'
        i = gen_id(alphabet=alpha)
        assert len(i) == Config.size
        assert set(i).issubset(set(alpha))

    def test_custom_size_and_alphabet(self):
        alpha = '1234567890qwerty'
        i = gen_id(alphabet=alpha, size=8)
        assert len(i) == 8
        assert set(i).issubset(set(alpha))

    def test_params_do_not_mutate_config(self):
        size_before = Config.size
        alphabet_before = Config.alphabet
        gen_id(alphabet=ascii_letters, size=7)
        assert Config.size == size_before
        assert Config.alphabet == alphabet_before

    def test_params_override_config(self):
        Config.size = 25
        Config.alphabet = digits
        try:
            assert len(gen_id()) == 25
            assert set(gen_id()).issubset(set(digits))
            assert len(gen_id(size=8)) == 8
            i = gen_id(alphabet=ascii_letters, size=12)
            assert len(i) == 12
            assert set(i).issubset(set(ascii_letters))
        finally:
            Config.size = 15
            Config.alphabet = ascii_letters + digits

    def test_size_too_small_raises(self):
        with pytest.raises(ValueError, match='The id size cannot be shorter than 5 characters.'):  # noqa
            gen_id(size=4)
        with pytest.raises(ValueError, match='The id size cannot be shorter than 5 characters.'):  # noqa
            gen_id(size=0)

    def test_alphabet_too_short_raises(self):
        with pytest.raises(ValueError, match='The alphabet must contain at least 10 characters.'):  # noqa
            gen_id(alphabet='abc')

    def test_alphabet_not_mutated_after_error(self):
        with pytest.raises(ValueError):
            gen_id(alphabet='abc')
        assert Config.alphabet == ascii_letters + digits
        with pytest.raises(ValueError):
            gen_id(size=3)
        assert Config.size == 15