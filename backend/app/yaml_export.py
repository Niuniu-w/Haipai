from collections import Counter

import yaml

from .schemas import ProjectData


def project_to_output(project: ProjectData) -> dict:
    return {
        "title": project.title,
        "genre": project.genre,
        "adaptation_mode": project.adaptationMode,
        "script_type": project.scriptType,
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
                "source_chapter": scene.sourceChapter,
                "title": scene.title,
                "location": scene.location,
                "time": scene.time,
                "atmosphere": scene.atmosphere,
                "characters": scene.characters,
                "actions": scene.actions,
                "dialogues": [
                    {
                        "character": dialogue.character,
                        "emotion": dialogue.emotion,
                        "line": dialogue.line,
                    }
                    for dialogue in scene.dialogues
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

    if not project.title.strip():
        errors.append("作品标题不能为空")
    if not project.genre.strip():
        errors.append("题材不能为空")
    if not project.adaptationMode.strip():
        errors.append("改编模式不能为空")
    if not project.scriptType.strip():
        errors.append("目标剧本类型不能为空")
    if duplicate_character_names:
        errors.append(f"人物名称重复：{'、'.join(sorted(duplicate_character_names))}")
    for character_index, character in enumerate(project.characters, start=1):
        if not character.name.strip() or not character.role.strip() or not character.description.strip():
            errors.append(f"第 {character_index} 位人物字段不完整")
    if not project.scenes:
        errors.append("至少需要一个剧本场景")
    if duplicate_scene_ids:
        errors.append(f"场景编号重复：{'、'.join(sorted(duplicate_scene_ids))}")

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
        if not scene.actions or any(not action.strip() for action in scene.actions):
            errors.append(f"{label}：动作描述不能为空")

        duplicate_scene_characters = {
            name for name, count in Counter(scene.characters).items() if name and count > 1
        }
        if duplicate_scene_characters:
            errors.append(f"{label}：出场人物重复：{'、'.join(sorted(duplicate_scene_characters))}")
        unknown_characters = {name for name in scene.characters if name not in character_names}
        if unknown_characters:
            errors.append(f"{label}：出场人物不在人物表：{'、'.join(sorted(unknown_characters))}")

        for dialogue_index, dialogue in enumerate(scene.dialogues, start=1):
            if not dialogue.character.strip() or not dialogue.emotion.strip() or not dialogue.line.strip():
                errors.append(f"{label}：第 {dialogue_index} 条对白字段不完整")
            elif dialogue.character not in scene.characters:
                errors.append(f"{label}：对白人物“{dialogue.character}”不在本场出场人物中")
    return errors


def dump_project_yaml(project: ProjectData) -> str:
    return yaml.safe_dump(
        project_to_output(project),
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )
