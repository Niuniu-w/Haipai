import json

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .llm_analyzer import LLMAnalysisError, extract_output_text
from .schemas import Character, Dialogue, Scene
from .settings import LLMSettings, get_llm_settings


class LLMPolishedDialogue(BaseModel):
    character: str = Field(min_length=1, max_length=30)
    emotion: str = Field(min_length=1, max_length=30)
    line: str = Field(min_length=1, max_length=300)

    model_config = ConfigDict(extra="forbid")


class LLMPolishedScene(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=100)
    time: str = Field(min_length=1, max_length=50)
    atmosphere: str = Field(min_length=1, max_length=100)
    characters: list[str] = Field(max_length=12)
    actions: list[str] = Field(min_length=1, max_length=12)
    dialogues: list[LLMPolishedDialogue] = Field(max_length=16)
    sourceSummary: str = Field(min_length=1, max_length=300)

    model_config = ConfigDict(extra="forbid")


def convert_polished_scene(result: LLMPolishedScene, scene: Scene, characters: list[Character]) -> Scene:
    known_names = {character.name for character in characters}
    if any(name not in known_names for name in result.characters):
        raise LLMAnalysisError("润色结果引用了人物表之外的人物")
    if any(dialogue.character not in result.characters for dialogue in result.dialogues):
        raise LLMAnalysisError("润色结果的对白人物不在本场出场人物中")
    return scene.model_copy(
        update={
            **result.model_dump(mode="json", exclude={"dialogues"}),
            "dialogues": [
                Dialogue(
                    id=f"{scene.id}-dialogue-{index + 1}",
                    **dialogue.model_dump(mode="json"),
                )
                for index, dialogue in enumerate(result.dialogues)
            ],
        }
    )


def polish_scene_with_model(
    scene: Scene,
    instruction: str,
    characters: list[Character],
    settings: LLMSettings | None = None,
    client: httpx.Client | None = None,
) -> Scene:
    settings = settings or get_llm_settings()
    if not settings.configured:
        raise LLMAnalysisError("未配置大模型 API Key")
    payload = {
        "model": settings.model,
        "store": False,
        "instructions": (
            "你是专业的中文影视编剧。只润色输入的单个场景，不改变来源章节和剧情事实，"
            "不得新增人物表之外的人物。请严格执行用户的调整指令。"
        ),
        "input": (
            f"调整指令：{instruction}\n"
            f"人物表：{'、'.join(character.name for character in characters)}\n"
            f"当前场景：{json.dumps(scene.model_dump(mode='json'), ensure_ascii=False)}"
        )[: settings.max_input_chars],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "scene_polish",
                "strict": True,
                "schema": LLMPolishedScene.model_json_schema(),
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
        result = LLMPolishedScene.model_validate_json(extract_output_text(response.json()))
        return convert_polished_scene(result, scene, characters)
    except (httpx.HTTPError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise LLMAnalysisError("大模型场景润色或结构化结果校验失败") from exc
    finally:
        if owns_client:
            client.close()


def polish_scene_locally(scene: Scene, instruction: str, characters: list[Character]) -> Scene:
    updated = scene.model_copy(deep=True)
    matched = False
    if any(keyword in instruction for keyword in ("夜晚", "夜景", "改成夜")):
        updated.time = "夜"
        matched = True
    if any(keyword in instruction for keyword in ("冲突", "紧张", "对峙")):
        updated.atmosphere = f"{updated.atmosphere.removesuffix('、冲突升级')}、冲突升级"
        updated.actions.append("人物的目标正面碰撞，现场气氛骤然收紧。")
        matched = True
    if any(keyword in instruction for keyword in ("对白", "对话")):
        speaker = updated.characters[0] if updated.characters else next((item.name for item in characters), "")
        if speaker:
            if speaker not in updated.characters:
                updated.characters.append(speaker)
            updated.dialogues.append(
                Dialogue(
                    id=f"{updated.id}-dialogue-{len(updated.dialogues) + 1}",
                    character=speaker,
                    emotion="坚定",
                    line="把真正想说的话说出来。",
                )
            )
        else:
            updated.actions.append("人物欲言又止，未说出口的话让气氛更紧张。")
        matched = True
    if not matched:
        updated.actions.append(f"根据调整指令强化画面表达：{instruction or '保持剧情并优化节奏'}。")
    return updated


def polish_scene_with_fallback(
    scene: Scene,
    instruction: str,
    characters: list[Character],
) -> tuple[Scene, str, str]:
    settings = get_llm_settings()
    if not settings.configured:
        return polish_scene_locally(scene, instruction, characters), "local-rules", ""
    try:
        polished = polish_scene_with_model(scene, instruction, characters, settings=settings)
        return polished, f"openai-responses:{settings.model}", ""
    except LLMAnalysisError as exc:
        return polish_scene_locally(scene, instruction, characters), "local-rules-fallback", str(exc)
