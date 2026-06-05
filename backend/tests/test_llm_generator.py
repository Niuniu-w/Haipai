import json

import backend.app.llm_generator as llm_generator
from backend.app.llm_analyzer import LLMAnalysisError
from backend.app.llm_generator import generate_script_with_fallback, generate_script_with_model
from backend.app.schemas import Chapter, Character
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
                "actions": ["林墨推开咖啡馆的门。"],
                "dialogues": [{"character": "林墨", "emotion": "疑惑", "line": "是谁留下的？"}],
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
        settings=settings,
        client=client,
    )

    assert scenes[0].id == "SC-01"
    assert scenes[0].sourceChapter == "第一章 雨夜"
    assert scenes[0].dialogues[0].id == "dialogue-1-1"
    assert client.request_json["text"]["format"]["type"] == "json_schema"


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
