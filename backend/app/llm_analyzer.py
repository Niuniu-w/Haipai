import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .llm_client import LLMAnalysisError, request_structured_output
from .schemas import Chapter, Character, Relationship
from .settings import LLMSettings, get_llm_settings
from .story_analyzer import analyze_story

colors = ["#e15d3f", "#587a6a", "#d09a3e", "#657792", "#66576d", "#8a6b4f"]


class LLMCharacter(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    role: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=200)

    model_config = ConfigDict(extra="forbid")


class LLMRelationship(BaseModel):
    from_: str = Field(alias="from", serialization_alias="from", min_length=1, max_length=20)
    to: str = Field(min_length=1, max_length=20)
    relation: str = Field(min_length=1, max_length=100)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class LLMChapterAnalysis(BaseModel):
    id: str
    summary: str = Field(min_length=1, max_length=300)
    keyEvents: list[str] = Field(min_length=1, max_length=5)

    model_config = ConfigDict(extra="forbid")


class LLMStoryAnalysis(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    genre: str = Field(min_length=1, max_length=50)
    era: str = Field(min_length=1, max_length=100)
    style: str = Field(min_length=1, max_length=100)
    characters: list[LLMCharacter] = Field(max_length=8)
    relationships: list[LLMRelationship] = Field(max_length=12)
    chapters: list[LLMChapterAnalysis]

    model_config = ConfigDict(extra="forbid")


def build_story_input(title: str, chapters: list[Chapter], max_chars: int) -> str:
    sections = [f"作品标题：{title}", "请分析以下小说章节："]
    remaining = max_chars - sum(len(section) for section in sections)

    for chapter in chapters:
        prefix = f"\n\n[{chapter.id}] {chapter.title}\n"
        if remaining <= len(prefix):
            break
        content = chapter.content[: max(0, remaining - len(prefix))]
        sections.append(prefix + content)
        remaining -= len(prefix) + len(content)

    return "".join(sections)


def convert_model_analysis(analysis: LLMStoryAnalysis, chapters: list[Chapter]) -> dict:
    chapter_analysis = {item.id: item for item in analysis.chapters}
    merged_chapters = []
    for chapter in chapters:
        item = chapter_analysis.get(chapter.id)
        merged_chapters.append(
            chapter.model_copy(
                update={
                    "summary": item.summary if item else chapter.summary,
                    "keyEvents": item.keyEvents if item else chapter.keyEvents,
                }
            )
        )

    characters = [
        Character(
            id=f"char-{index + 1}",
            name=character.name,
            role=character.role,
            description=character.description,
            color=colors[index % len(colors)],
        )
        for index, character in enumerate(analysis.characters)
    ]
    relationships = [
        Relationship(**relationship.model_dump(mode="json", by_alias=True)) for relationship in analysis.relationships
    ]
    return {
        "summary": analysis.summary,
        "genre": analysis.genre,
        "era": analysis.era,
        "style": analysis.style,
        "characters": characters,
        "relationships": relationships,
        "chapters": merged_chapters,
    }


def analyze_story_with_model(
    title: str,
    chapters: list[Chapter],
    settings: LLMSettings | None = None,
    client: httpx.Client | None = None,
) -> dict:
    settings = settings or get_llm_settings()
    if not settings.configured:
        raise LLMAnalysisError("未配置大模型 API Key")

    try:
        output = request_structured_output(
            settings,
            (
                "你是专业的中文小说故事分析师。请只根据输入章节分析故事，"
                "不要虚构原文不存在的人物或事件。人物名称必须保持一致，章节 id 必须原样返回。"
            ),
            build_story_input(title, chapters, settings.max_input_chars),
            LLMStoryAnalysis.model_json_schema(by_alias=True),
            "story_analysis",
            client,
        )
        analysis = LLMStoryAnalysis.model_validate_json(output)
        return convert_model_analysis(analysis, chapters)
    except (LLMAnalysisError, ValidationError, ValueError) as exc:
        raise LLMAnalysisError("大模型调用或结构化结果校验失败") from exc


def analyze_story_with_fallback(title: str, chapters: list[Chapter]) -> tuple[dict, str, str]:
    settings = get_llm_settings()
    if not settings.configured:
        return analyze_story(title, chapters), "local-rules", ""

    try:
        return analyze_story_with_model(title, chapters, settings=settings), settings.mode, ""
    except LLMAnalysisError as exc:
        return analyze_story(title, chapters), "local-rules-fallback", str(exc)
