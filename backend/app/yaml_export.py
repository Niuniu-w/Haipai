from collections import Counter
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .schemas import ProjectData

SCRIPT_SCHEMA_VERSION = "storyforge-script/v2"


class ExportChapter(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    key_events: list[str] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class ExportCharacter(BaseModel):
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    description: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class ExportAction(BaseModel):
    type: Literal["action"]
    action: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class ExportDialogue(BaseModel):
    type: Literal["dialogue"]
    action: str = Field(min_length=1)
    character: str = Field(min_length=1)
    emotion: str = Field(min_length=1)
    line: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class ExportScene(BaseModel):
    id: str = Field(min_length=1)
    source_chapter_id: str = Field(min_length=1)
    source_chapter: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str = Field(min_length=1)
    time: str = Field(min_length=1)
    atmosphere: str = Field(min_length=1)
    characters: list[str]
    content: list[ExportAction | ExportDialogue] = Field(min_length=1)
    source_summary: str = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


class ScriptExport(BaseModel):
    schema_version: Literal["storyforge-script/v2"]
    title: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    adaptation_mode: str = Field(min_length=1)
    script_type: str = Field(min_length=1)
    chapters: list[ExportChapter] = Field(min_length=1)
    characters: list[ExportCharacter]
    scenes: list[ExportScene] = Field(min_length=1)
    model_config = ConfigDict(extra="forbid")


def project_to_output(project: ProjectData) -> dict:
    return {
        "schema_version": SCRIPT_SCHEMA_VERSION,
        "title": project.title,
        "genre": project.genre,
        "adaptation_mode": project.adaptationMode,
        "script_type": project.scriptType,
        "chapters": [
            {
                "id": chapter.id,
                "title": chapter.title,
                "summary": chapter.summary,
                "key_events": chapter.keyEvents,
            }
            for chapter in project.chapters
        ],
        "characters": [
            {
                "name": character.name,
                "role": character.role,
                "description": character.description,
            }
            for character in project.characters
        ],
        "scenes": [
            {
                "id": scene.id,
                "source_chapter_id": scene.chapterId,
                "source_chapter": scene.sourceChapter,
                "title": scene.title,
                "location": scene.location,
                "time": scene.time,
                "atmosphere": scene.atmosphere,
                "characters": scene.characters,
                "content": [
                    {
                        "type": item.type,
                        "action": item.action,
                        **(
                            {
                                "character": item.character,
                                "emotion": item.emotion,
                                "line": item.line,
                            }
                            if item.type == "dialogue"
                            else {}
                        ),
                    }
                    for item in scene.content
                ],
                "source_summary": scene.sourceSummary,
            }
            for scene in project.scenes
        ],
    }


def validate_project_script(project: ProjectData) -> list[str]:
    errors: list[str] = []
    chapter_ids = {chapter.id for chapter in project.chapters}
    chapter_titles = {chapter.id: chapter.title for chapter in project.chapters}
    character_names = {character.name.strip() for character in project.characters if character.name.strip()}
    duplicate_character_names = {
        name
        for name, count in Counter(character.name.strip() for character in project.characters).items()
        if name and count > 1
    }
    duplicate_scene_ids = {
        scene_id
        for scene_id, count in Counter(scene.id.strip() for scene in project.scenes).items()
        if scene_id and count > 1
    }
    duplicate_chapter_ids = {
        chapter_id
        for chapter_id, count in Counter(chapter.id.strip() for chapter in project.chapters).items()
        if chapter_id and count > 1
    }

    if not project.title.strip():
        errors.append("作品标题不能为空")
    if not project.genre.strip():
        errors.append("题材不能为空")
    if not project.adaptationMode.strip():
        errors.append("改编模式不能为空")
    if not project.scriptType.strip():
        errors.append("目标剧本类型不能为空")
    if not project.chapters:
        errors.append("至少需要一个来源章节")
    if duplicate_chapter_ids:
        errors.append(f"章节 ID 重复：{'、'.join(sorted(duplicate_chapter_ids))}")
    for chapter_index, chapter in enumerate(project.chapters, start=1):
        if not chapter.id.strip() or not chapter.title.strip() or not chapter.summary.strip():
            errors.append(f"第 {chapter_index} 个章节字段不完整")
        if not chapter.keyEvents or any(not event.strip() for event in chapter.keyEvents):
            errors.append(f"{chapter.title or f'第 {chapter_index} 章'}：关键事件不能为空")
        if not any(scene.chapterId == chapter.id for scene in project.scenes):
            errors.append(f"{chapter.title or f'第 {chapter_index} 章'}：至少需要一个场景")
    if duplicate_character_names:
        errors.append(f"人物名称重复：{'、'.join(sorted(duplicate_character_names))}")
    for character_index, character in enumerate(project.characters, start=1):
        if not character.name.strip() or not character.role.strip() or not character.description.strip():
            errors.append(f"第 {character_index} 位人物字段不完整")
    if not project.scenes:
        errors.append("至少需要一个剧本场景")
    if duplicate_scene_ids:
        errors.append(f"场景编号重复：{'、'.join(sorted(duplicate_scene_ids))}")
    for relationship_index, relationship in enumerate(project.relationships, start=1):
        if not relationship.from_.strip() or not relationship.to.strip() or not relationship.relation.strip():
            errors.append(f"第 {relationship_index} 条人物关系字段不完整")
        elif relationship.from_ not in character_names or relationship.to not in character_names:
            errors.append(f"第 {relationship_index} 条人物关系引用了人物表之外的人物")

    required_scene_fields = {
        "id": "场景编号",
        "title": "场景标题",
        "location": "地点",
        "time": "时间",
        "atmosphere": "氛围",
        "sourceSummary": "来源剧情摘要",
    }
    for index, scene in enumerate(project.scenes, start=1):
        label = scene.id.strip() or f"第 {index} 场"
        for field_name, field_label in required_scene_fields.items():
            if not getattr(scene, field_name).strip():
                errors.append(f"{label}：{field_label}不能为空")
        if scene.chapterId not in chapter_ids:
            errors.append(f"{label}：来源章节不存在")
        elif scene.sourceChapter != chapter_titles[scene.chapterId]:
            errors.append(f"{label}：来源章节标题与章节数据不一致")
        if not scene.content:
            errors.append(f"{label}：剧本内容不能为空")

        duplicate_scene_characters = {
            name for name, count in Counter(scene.characters).items() if name and count > 1
        }
        if duplicate_scene_characters:
            errors.append(f"{label}：出场人物重复：{'、'.join(sorted(duplicate_scene_characters))}")
        unknown_characters = {name for name in scene.characters if name not in character_names}
        if unknown_characters:
            errors.append(f"{label}：出场人物不在人物表：{'、'.join(sorted(unknown_characters))}")

        for item_index, item in enumerate(scene.content, start=1):
            if not item.action.strip():
                errors.append(f"{label}：第 {item_index} 条内容的动作不能为空")
            if item.type == "dialogue":
                if not item.character.strip() or not item.emotion.strip() or not item.line.strip():
                    errors.append(f"{label}：第 {item_index} 条对白字段不完整")
                elif item.character not in scene.characters:
                    errors.append(f"{label}：对白人物“{item.character}”不在本场出场人物中")
    return errors


def dump_project_yaml(project: ProjectData) -> str:
    output = ScriptExport.model_validate(project_to_output(project)).model_dump(mode="json")
    return yaml.safe_dump(
        output,
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )


def script_schema() -> dict:
    return ScriptExport.model_json_schema()
