from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from services.cache_service import CacheService

router = APIRouter(prefix="/testtest", tags=["test"])


@router.get("/test")
async def test(
        code_1: str, code_2: str, cache_service: CacheService = Depends(CacheService)
):
    cache_key = f"test:{code_1}:{code_2}"

    if cached_result := await cache_service.get_cache(cache_key):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=cached_result,
            headers={"X-Cache": "HIT"},
        )

    test = [code_1, code_2]
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Route not found"
        )

    await cache_service.set_cache(cache_key, test)
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=test, headers={"X-Cache": "MISS"}
    )
