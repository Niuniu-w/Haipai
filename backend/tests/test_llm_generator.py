import json

import backend.app.llm_generator as llm_generator
from backend.app.llm_analyzer import LLMAnalysisError
from backend.app.llm_generator import generate_script_with_fallback, generate_script_with_model
from backend.app.schemas import Chapter, Character
from backend.app.script_generator import build_local_scenes
from backend.app.settings import LLMSettings


class FakeResponse:
    def __init__(self, data: dict) -> None:
        self.data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.data


class FakeClient:
    def __init__(self, response_data: dict) -> None:
        self.response_data = response_data
        self.request_json: dict = {}

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.request_json = kwargs["json"]
        return FakeResponse(self.response_data)


def test_model_script_generation_validates_and_converts_scenes() -> None:
    chapters = [
        Chapter(
            id="chapter-1",
            title="第一章 雨夜",
            content="记者林墨走进咖啡馆。",
            summary="林墨进入咖啡馆",
            keyEvents=["进入咖啡馆"],
        )
    ]
    characters = [
        Character(id="char-1", name="林墨", role="记者", description="调查者", color="#000000")
    ]
    output = {
        "scenes": [
            {
                "chapterId": "chapter-1",
                "title": "雨夜来信",
                "location": "咖啡馆",
                "time": "夜",
                "atmosphere": "紧张",
                "characters": ["林墨"],
                "content": [
                    {"type": "action", "action": "林墨推开咖啡馆的门。"},
                    {
                        "type": "dialogue",
                        "action": "林墨停下脚步，警惕地环顾四周。",
                        "character": "林墨",
                        "emotion": "疑惑",
                        "line": "是谁留下的？",
                    },
                ],
                "sourceSummary": "林墨进入咖啡馆",
            }
        ]
    }
    client = FakeClient(
        {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": json.dumps(output, ensure_ascii=False)}
                    ]
                }
            ]
        }
    )
    settings = LLMSettings(
        api_key="test-key",
        base_url="https://api.example.com/v1",
        model="test-model",
        timeout_seconds=10,
        max_input_chars=10000,
    )

    scenes = generate_script_with_model(
        "测试故事",
        "故事概要",
        "悬疑",
        "紧凑",
        "忠于原著",
        "电影",
        chapters,
        characters,
        dialogue_density="密集",
        target_scene_count=2,
        settings=settings,
        client=client,
    )

    assert scenes[0].id == "SC-01"
    assert scenes[0].sourceChapter == "第一章 雨夜"
    assert scenes[0].content[1].id == "SC-01-content-2"
    assert scenes[0].content[1].action == "林墨停下脚步，警惕地环顾四周。"
    assert client.request_json["text"]["format"]["type"] == "json_schema"
    assert "对白密度：密集" in client.request_json["input"]
    assert "目标场景数：2" in client.request_json["input"]
    assert "避免旁白" in client.request_json["input"]


def test_local_generation_defaults_to_dialogue_forward_scenes() -> None:
    chapters = [
        Chapter(
            id="chapter-1",
            title="第一章 线索",
            content="林墨走进咖啡馆。他收到匿名信。他发现信中藏着地址。他决定立刻出发。",
            summary="林墨收到匿名信",
            keyEvents=["收到匿名信"],
        )
    ]
    characters = [
        Character(id="char-1", name="林墨", role="记者", description="调查者", color="#000000")
    ]

    scene = build_local_scenes(chapters, characters, "悬疑", "紧凑")[0]
    dialogues = [item for item in scene.content if item.type == "dialogue"]
    actions = [item for item in scene.content if item.type == "action"]

    assert len(dialogues) > len(actions)
    assert all(item.action and item.character and item.line for item in dialogues)


def test_single_sentence_scene_with_character_becomes_dialogue() -> None:
    chapters = [
        Chapter(
            id="chapter-1",
            title="第一章 出发",
            content="林墨决定立刻出发。",
            summary="林墨决定出发",
            keyEvents=["决定出发"],
        )
    ]
    characters = [
        Character(id="char-1", name="林墨", role="记者", description="调查者", color="#000000")
    ]

    scene = build_local_scenes(chapters, characters, "悬疑", "紧凑")[0]

    assert len(scene.content) == 1
    assert scene.content[0].type == "dialogue"
    assert scene.content[0].action


def test_model_script_failure_falls_back_to_local_rules(monkeypatch) -> None:
    monkeypatch.setenv("STORYFORGE_LLM_API_KEY", "test-key")
    chapters = [
        Chapter(
            id=f"chapter-{index}",
            title=f"第{index}章",
            content="记者林墨走进咖啡馆。",
            summary="林墨进入咖啡馆",
            keyEvents=["进入咖啡馆"],
        )
        for index in range(1, 4)
    ]
    characters = [
        Character(id="char-1", name="林墨", role="记者", description="调查者", color="#000000")
    ]

    def fail_generation(*args, **kwargs):
        raise LLMAnalysisError("模拟剧本生成失败")

    monkeypatch.setattr(llm_generator, "generate_script_with_model", fail_generation)
    scenes, mode, error = generate_script_with_fallback(
        "测试故事",
        "故事概要",
        "悬疑",
        "紧凑",
        "忠于原著",
        "电影",
        chapters,
        characters,
    )

    assert len(scenes) == 3
    assert mode == "local-rules-fallback"
    assert error == "模拟剧本生成失败"
