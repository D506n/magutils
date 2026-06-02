from pathlib import Path

from .fields import field


class LoggingMixin:
    LOG_LEVEL: str = field('INFO')
    # --- Логирование: консоль ---
    CONSOLE_LOG_JSON: bool = field(False)
    CONSOLE_LOG_LEVEL: str = field("INFO")
    CONSOLE_LOG_COLOR: bool = field(True)
    CONSOLE_LOG_NOCUT: bool = field(False)

    # --- Логирование: файл ---
    FILE_LOG_LEVEL: str = field("INFO")
    FILE_LOG_PATH: Path = field(Path("./data/logs/log.log"))
    FILE_LOG_NOCUT: bool = field(True)
    FILE_LOG_ON_EXPIRE: str = field("compress")
    FILE_LOG_MAXBYTES: int | None = field(None)
    FILE_LOG_ROTATION_BY_DT: bool = field(True)


class DBMixin:
    DB_TYPE: str = field('sqlite')
    DB_USERNAME: str | None = field(None)
    DB_PASSWORD: str | None = field(None)
    DB_HOST: str | None = field(None)
    DB_PORT: int | None = field(None)
    DB_NAME: str | None = field(None)
    DB_PATH: Path | None = field(None)
    DB_SCHEMA: str = field('public')


class RedisMixin:
    REDIS_HOST: str = field('localhost')
    REDIS_PORT: int = field(6379)
    REDIS_DB: int = field(0)
    REDIS_PASSWORD: str | None = field(None)


class CORSMixin:
    CORS_ALLOW_ORIGINS: list[str] = field(default_factory=lambda: ["http://localhost:5173"])  #noqa
    CORS_ALLOW_CREDENTIALS: bool = field(True)
    CORS_ALLOW_METHODS: list[str] = field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: list[str] = field(default_factory=lambda: ["*"])


class APIMixin:
    API_HOST: str = field('0.0.0.0')
    API_PORT: int = field(8506)