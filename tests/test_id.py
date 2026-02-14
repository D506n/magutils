from string import ascii_letters, digits

import pytest

from src.utils.id import Config, gen_id, is_valid


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