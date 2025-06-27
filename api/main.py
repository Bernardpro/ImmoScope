import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings

from routes import auth

from routes import data, cache
from routes import proprietes, comment


from services.resource_monitor import ResourceMonitoringMiddleware

logger = logging.getLogger("app")


class Settings(BaseSettings):
    APP_TITLE: str = "HomePedia API"
    APP_DESCRIPTION: str = "API for real estate data and user management"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: list = [
        "http://localhost:5174",
        "http://localhost:82",
        "http://localhost:3000",
        "https://api.homepedia.spectrum-app.cloud",
        "https://homepedia.spectrum-app.cloud",
        "35.192.206.86"
    ]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()


def create_app():
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(ResourceMonitoringMiddleware)

    app.include_router(cache.router)
    
    app.include_router(comment.router)

    app.include_router(auth.router)

    app.include_router(data.router)

    app.include_router(proprietes.router)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global error: {exc}")
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    @app.get("/")
    async def root():
        return {
            "message": "HomePedia API",
            "version": settings.APP_VERSION,
            "endpoints": {
                "auth": "/user",
                "proprietes": "/proprietes",
                "cache": "/cache",
                "test": "/test",
            },
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
