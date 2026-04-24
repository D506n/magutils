from src.models.responses.ok import OK

from .api_router import router


@router.get('/')
async def health_check() -> OK:
    return OK.true()