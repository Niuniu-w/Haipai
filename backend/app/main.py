from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_database
from .projects import router as projects_router
from .schemas import AIStatusResponse
from .settings import get_llm_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="StoryForge API",
    description="织幕 StoryForge 后端 API",
    version="0.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(127\.0\.0\.1|localhost):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
