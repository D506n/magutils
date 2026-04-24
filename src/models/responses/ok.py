from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field


class OK(BaseModel):
    success: bool = Field(True)
    details: Optional[dict] = Field(default_factory=dict)

    @classmethod
    @lru_cache(1)
    def true(cls):
        return cls(success=True)

    @classmethod
    def false(cls, **details):
        return cls(success=False, details=details)