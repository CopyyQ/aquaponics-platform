from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.deps import AccountAuthError
from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    default_response_class=ORJSONResponse,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(AccountAuthError)
async def account_auth_error_handler(_, exc: AccountAuthError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=401,
        content={"code": exc.code, "detail": exc.detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
