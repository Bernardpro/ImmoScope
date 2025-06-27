from fastapi import APIRouter, HTTPException, status, Depends
from services.cache_service import CacheService

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/clear")
async def clear_cache(
    pattern: str = None, cache_service: CacheService = Depends(CacheService)
):
    """Clear all cache or pattern-specific cache"""
    success = await cache_service.clear_cache(pattern)
    if success:
        return {"message": "Cache cleared successfully"}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error clearing cache"
    )


@router.delete("/{key}")
async def delete_key(key: str, cache_service: CacheService = Depends(CacheService)):
    """Delete specific cache key"""
    success = await cache_service.delete_key(key)
    if success:
        return {"message": f"Cache key {key} deleted"}
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error deleting key {key}",
    )


@router.get("/ttl/{key}")
async def get_ttl(key: str, cache_service: CacheService = Depends(CacheService)):
    """Get TTL for specific cache key"""
    ttl = await cache_service.get_ttl(key)
    if ttl is not None:
        return {"ttl": ttl}
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Key {key} not found"
    )
