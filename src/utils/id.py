from string import ascii_letters, digits

import nanoid

DEFAULT_ALPHABET = ascii_letters + digits


def gen_id(alphabet: str = DEFAULT_ALPHABET, size: int = 15):
    # 3 триллиона idшников исчерпаются примерно никогда https://zelark.github.io/nano-id-cc/
    return nanoid.generate(alphabet, size)