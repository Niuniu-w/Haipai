import json
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .llm_client import LLMAnalysisError, request_structured_output
from .schemas import Character, Scene, SceneContentItem
from .settings import LLMSettings, get_llm_settings


class LLMPolishedAction(BaseModel):
    type: Literal["action"]
    action: str = Field(min_length=1, max_length=500)
    model_config = ConfigDict(extra="forbid")


class LLMPolishedDialogue(BaseModel):
    type: Literal["dialogue"]
    action: str = Field(min_length=1, max_length=500)
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
    content: list[LLMPolishedAction | LLMPolishedDialogue] = Field(min_length=1, max_length=24)
    sourceSummary: str = Field(min_length=1, max_length=300)

    model_config = ConfigDict(extra="forbid")


def convert_polished_scene(result: LLMPolishedScene, scene: Scene, characters: list[Character]) -> Scene:
    known_names = {character.name for character in characters}
    if any(name not in known_names for name in result.characters):
        raise LLMAnalysisError("润色结果引用了人物表之外的人物")
    if any(item.type == "dialogue" and item.character not in result.characters for item in result.content):
        raise LLMAnalysisError("润色结果的对白人物不在本场出场人物中")
    return scene.model_copy(
        update={
            **result.model_dump(mode="json", exclude={"content"}),
            "content": [
                SceneContentItem(
                    id=f"{scene.id}-content-{index + 1}",
                    **item.model_dump(mode="json"),
                )
                for index, item in enumerate(result.content)
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
    try:
        output = request_structured_output(
            settings,
            (
                "你是专业的中文影视编剧。只润色输入的单个场景，不改变来源章节和剧情事实，"
                "不得新增人物表之外的人物。请严格执行用户的调整指令。场景 content 必须按演出顺序"
                "混排动作与对白，每条对白都必须带有说话时对应的 action。"
            ),
            (
                f"调整指令：{instruction}\n"
                f"人物表：{'、'.join(character.name for character in characters)}\n"
                f"当前场景：{json.dumps(scene.model_dump(mode='json'), ensure_ascii=False)}"
            )[: settings.max_input_chars],
            LLMPolishedScene.model_json_schema(),
            "scene_polish",
            client,
        )
        result = LLMPolishedScene.model_validate_json(output)
        return convert_polished_scene(result, scene, characters)
    except (LLMAnalysisError, ValidationError, ValueError) as exc:
        raise LLMAnalysisError("大模型场景润色或结构化结果校验失败") from exc


def polish_scene_locally(scene: Scene, instruction: str, characters: list[Character]) -> Scene:
    updated = scene.model_copy(deep=True)
    matched = False
    if any(keyword in instruction for keyword in ("夜晚", "夜景", "改成夜")):
        updated.time = "夜"
        matched = True
    if any(keyword in instruction for keyword in ("冲突", "紧张", "对峙")):
        updated.atmosphere = f"{updated.atmosphere.removesuffix('、冲突升级')}、冲突升级"
        updated.content.append(
            SceneContentItem(
                id=f"{updated.id}-content-{len(updated.content) + 1}",
                type="action",
                action="人物的目标正面碰撞，现场气氛骤然收紧。",
            )
        )
        matched = True
    if any(keyword in instruction for keyword in ("对白", "对话")):
        speaker = updated.characters[0] if updated.characters else next((item.name for item in characters), "")
        if speaker:
            if speaker not in updated.characters:
                updated.characters.append(speaker)
            updated.content.append(
                SceneContentItem(
                    id=f"{updated.id}-content-{len(updated.content) + 1}",
                    type="dialogue",
                    action=f"{speaker}直视对方，把压在心里的话说出口。",
                    character=speaker,
                    emotion="坚定",
                    line="把真正想说的话说出来。",
                )
            )
        else:
            updated.content.append(
                SceneContentItem(
                    id=f"{updated.id}-content-{len(updated.content) + 1}",
                    type="action",
                    action="人物欲言又止，未说出口的话让气氛更紧张。",
                )
            )
        matched = True
    if not matched:
        updated.content.append(
            SceneContentItem(
                id=f"{updated.id}-content-{len(updated.content) + 1}",
                type="action",
                action=f"根据调整指令强化画面表达：{instruction or '保持剧情并优化节奏'}。",
            )
        )
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
        return polished, settings.mode, ""
    except LLMAnalysisError as exc:
        return polish_scene_locally(scene, instruction, characters), "local-rules-fallback", str(exc)
