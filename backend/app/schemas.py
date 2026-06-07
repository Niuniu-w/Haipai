from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Chapter(BaseModel):
    id: str
    title: str
    content: str
    summary: str
    keyEvents: list[str]


class Character(BaseModel):
    id: str
    name: str
    role: str
    description: str
    color: str


class Relationship(BaseModel):
    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    relation: str

    model_config = ConfigDict(populate_by_name=True)


class SceneContentItem(BaseModel):
    id: str
    type: Literal["action", "dialogue"]
    action: str
    character: str = ""
    emotion: str = ""
    line: str = ""


class Scene(BaseModel):
    id: str
    chapterId: str
    sourceChapter: str
    title: str
    location: str
    time: str
    atmosphere: str
    characters: list[str]
    content: list[SceneContentItem]
    sourceSummary: str

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_content(cls, value):
        if not isinstance(value, dict) or "content" in value:
            return value
        migrated = dict(value)
        actions = migrated.pop("actions", [])
        dialogues = migrated.pop("dialogues", [])
        migrated["content"] = [
            {
                "id": f"{migrated.get('id', 'scene')}-action-{index + 1}",
                "type": "action",
                "action": action,
            }
            for index, action in enumerate(actions)
        ] + [
            {
                "id": dialogue.get("id", f"{migrated.get('id', 'scene')}-dialogue-{index + 1}"),
                "type": "dialogue",
                "action": f"{dialogue.get('character', '人物')}准备开口。",
                "character": dialogue.get("character", ""),
                "emotion": dialogue.get("emotion", ""),
                "line": dialogue.get("line", ""),
            }
            for index, dialogue in enumerate(dialogues)
        ]
        return migrated


class GenerationChapterState(BaseModel):
    chapter_id: str
    status: str = "pending"
    mode: str = ""
    attempts: int = 0
    error: str = ""
    scene_count: int = 0


class ProjectData(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    filename: str
    rawText: str
    genre: str
    style: str
    era: str
    summary: str
    adaptationMode: str
    scriptType: str
    dialogueDensity: Literal["少量", "均衡", "密集"] = "密集"
    targetSceneCount: int = Field(default=0, ge=0, le=500)
    chapters: list[Chapter]
    characters: list[Character]
    relationships: list[Relationship]
    scenes: list[Scene]
    updatedAt: str
    revision: int = 0
    analysisStatus: str = "pending"
    analysisMode: str = ""
    analysisError: str = ""
    analysisAttempts: int = 0
    generationStatus: str = "pending"
    generationMode: str = ""
    generationError: str = ""
    generationAttempts: int = 0
    generationChapters: list[GenerationChapterState] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    id: str
    data: ProjectData
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectSummary(BaseModel):
    id: str
    title: str
    chapter_count: int
    scene_count: int
    updated_at: datetime


class ChapterParseRequest(BaseModel):
    raw_text: str


class ChapterParseResponse(BaseModel):
    chapters: list[Chapter]
    chapter_count: int
    valid: bool
    minimum_required: int = 3


class StoryAnalysisResponse(BaseModel):
    summary: str
    genre: str
    era: str
    style: str
    characters: list[Character]
    relationships: list[Relationship]
    chapters: list[Chapter]
    analysis_status: str
    analysis_mode: str
    analysis_attempts: int
    analysis_error: str


class AIStatusResponse(BaseModel):
    configured: bool
    provider: str
    model: str
    fallback: str


class ScriptGenerationResponse(BaseModel):
    scenes: list[Scene]
    scene_count: int
    generation_status: str
    generation_mode: str
    generation_attempts: int
    generation_error: str
    chapter_statuses: list[GenerationChapterState]


class GenerationStatusResponse(BaseModel):
    status: str
    mode: str
    attempts: int
    error: str
    scene_count: int
    chapter_statuses: list[GenerationChapterState]


class ScriptValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    scene_count: int


class ScenePolishRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=1000)


class ScenePolishResponse(BaseModel):
    scene: Scene
    mode: str
    error: str
