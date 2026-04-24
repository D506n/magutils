from src.utils.env import environ
from src.utils.env.mixins import APIMixin


@environ()
class Env(APIMixin):
    pass