from contextlib import asynccontextmanager
from secrets import compare_digest

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import init_database
from .projects import router as projects_router
from .schemas import AIStatusResponse
from .settings import get_api_token, get_cors_origins, get_llm_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="StoryForge API",
    description="织幕 StoryForge 后端 API",
    version="0.7.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_api_token(request, call_next):
    token = get_api_token()
    if token and request.url.path.startswith("/api/") and request.url.path != "/api/health":
        supplied = request.headers.get("x-api-key", "")
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            supplied = authorization.removeprefix("Bearer ").strip()
        if not supplied or not compare_digest(supplied, token):
            return JSONResponse(status_code=401, content={"detail": "缺少或无效的 API Token"})
    return await call_next(request)


@app.get("/api/health", tags=["系统"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/ai/status", response_model=AIStatusResponse, tags=["系统"])
def ai_status() -> AIStatusResponse:
    settings = get_llm_settings()
    return AIStatusResponse(
        configured=settings.configured,
        provider="openai-responses",
        model=settings.model,
        fallback="local-rules",
    )


app.include_router(projects_router)
