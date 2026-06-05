import json

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .llm_analyzer import LLMAnalysisError, extract_output_text
from .schemas import Chapter, Character, Dialogue, Scene
from .script_generator import build_local_scenes
from .settings import LLMSettings, get_llm_settings


class LLMDialogue(BaseModel):
    character: str = Field(min_length=1, max_length=30)
    emotion: str = Field(min_length=1, max_length=30)
    line: str = Field(min_length=1, max_length=300)

    model_config = ConfigDict(extra="forbid")


class LLMScene(BaseModel):
    chapterId: str
    title: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=100)
    time: str = Field(min_length=1, max_length=50)
    atmosphere: str = Field(min_length=1, max_length=100)
    characters: list[str] = Field(max_length=12)
    actions: list[str] = Field(min_length=1, max_length=8)
    dialogues: list[LLMDialogue] = Field(max_length=12)
    sourceSummary: str = Field(min_length=1, max_length=300)

    model_config = ConfigDict(extra="forbid")


class LLMScript(BaseModel):
    scenes: list[LLMScene] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


def build_generation_input(
    title: str,
    summary: str,
    genre: str,
    style: str,
    adaptation_mode: str,
    script_type: str,
    chapters: list[Chapter],
    characters: list[Character],
    max_chars: int,
) -> str:
    character_text = "、".join(f"{item.name}（{item.role}）" for item in characters) or "暂无人物表"
    header = (
        f"作品标题：{title}\n故事概要：{summary}\n题材：{genre}\n风格：{style}\n"
        f"改编模式：{adaptation_mode}\n目标剧本类型：{script_type}\n人物表：{character_text}\n"
        "请将以下章节改编为结构化剧本场景，每章至少生成一个场景，chapterId 必须原样返回："
    )
    sections = [header]
    remaining = max_chars - len(header)
    for chapter in chapters:
        prefix = f"\n\n[{chapter.id}] {chapter.title}\n章节摘要：{chapter.summary}\n原文："
        if remaining <= len(prefix):
            break
        content = chapter.content[: max(0, remaining - len(prefix))]
        sections.append(prefix + content)
        remaining -= len(prefix) + len(content)
    return "".join(sections)


def convert_model_script(script: LLMScript, chapters: list[Chapter]) -> list[Scene]:
    chapter_map = {chapter.id: chapter for chapter in chapters}
    scenes: list[Scene] = []
    for index, scene in enumerate(script.scenes):
        chapter = chapter_map.get(scene.chapterId)
        if chapter is None:
            continue
        scenes.append(
            Scene(
                id=f"SC-{index + 1:02d}",
                chapterId=chapter.id,
                sourceChapter=chapter.title,
                title=scene.title,
                location=scene.location,
                time=scene.time,
                atmosphere=scene.atmosphere,
                characters=scene.characters,
                actions=scene.actions,
                dialogues=[
                    Dialogue(
                        id=f"dialogue-{index + 1}-{dialogue_index + 1}",
                        **dialogue.model_dump(mode="json"),
                    )
                    for dialogue_index, dialogue in enumerate(scene.dialogues)
                ],
                sourceSummary=scene.sourceSummary,
            )
        )
    if not scenes:
        raise LLMAnalysisError("模型未返回有效场景")
    return scenes


def generate_script_with_model(
    title: str,
    summary: str,
    genre: str,
    style: str,
    adaptation_mode: str,
    script_type: str,
    chapters: list[Chapter],
    characters: list[Character],
    settings: LLMSettings | None = None,
    client: httpx.Client | None = None,
) -> list[Scene]:
    settings = settings or get_llm_settings()
    if not settings.configured:
        raise LLMAnalysisError("未配置大模型 API Key")

    payload = {
        "model": settings.model,
        "store": False,
        "instructions": (
            "你是专业的中文影视编剧。请忠于输入原文，将每章改编成可拍摄的结构化场景。"
            "不要虚构改变主线的新事件，动作应可视化，对白应符合人物身份。"
        ),
        "input": build_generation_input(
            title,
            summary,
            genre,
            style,
            adaptation_mode,
            script_type,
            chapters,
            characters,
            settings.max_input_chars,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "script_generation",
                "strict": True,
                "schema": LLMScript.model_json_schema(),
            }
        },
    }
    owns_client = client is None
    client = client or httpx.Client(timeout=settings.timeout_seconds)
    try:
        response = client.post(
            f"{settings.base_url}/responses",
            headers={"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        script = LLMScript.model_validate_json(extract_output_text(response.json()))
        return convert_model_script(script, chapters)
    except (httpx.HTTPError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise LLMAnalysisError("大模型剧本生成或结构化结果校验失败") from exc
    finally:
        if owns_client:
            client.close()


def generate_script_with_fallback(
    title: str,
    summary: str,
    genre: str,
    style: str,
    adaptation_mode: str,
    script_type: str,
    chapters: list[Chapter],
    characters: list[Character],
) -> tuple[list[Scene], str, str]:
    settings = get_llm_settings()
    if not settings.configured:
        return build_local_scenes(chapters, characters, genre, style), "local-rules", ""
    try:
        scenes = generate_script_with_model(
            title,
            summary,
            genre,
            style,
            adaptation_mode,
            script_type,
            chapters,
            characters,
            settings=settings,
        )
        return scenes, f"openai-responses:{settings.model}", ""
    except LLMAnalysisError as exc:
        return build_local_scenes(chapters, characters, genre, style), "local-rules-fallback", str(exc)
