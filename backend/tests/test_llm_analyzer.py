import json

import backend.app.llm_analyzer as llm_analyzer
from backend.app.llm_analyzer import LLMAnalysisError, analyze_story_with_fallback, analyze_story_with_model
from backend.app.schemas import Chapter
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
        self.request_url = ""

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.request_url = url
        self.request_json = kwargs["json"]
        return FakeResponse(self.response_data)


def test_model_analysis_uses_structured_output_and_validates_result() -> None:
    chapters = [
        Chapter(
            id="chapter-1",
            title="第一章",
            content="记者林墨开始调查。",
            summary="原摘要",
            keyEvents=["原事件"],
        )
    ]
    model_output = {
        "summary": "林墨开始调查一桩案件。",
        "genre": "悬疑",
        "era": "当代",
        "style": "紧凑",
        "characters": [{"name": "林墨", "role": "记者", "description": "负责调查案件。"}],
        "relationships": [],
        "chapters": [{"id": "chapter-1", "summary": "林墨开始调查。", "keyEvents": ["开始调查"]}],
    }
    client = FakeClient(
        {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps(model_output, ensure_ascii=False),
                        }
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

    result = analyze_story_with_model("测试故事", chapters, settings=settings, client=client)

    assert result["genre"] == "悬疑"
    assert result["characters"][0].name == "林墨"
    assert result["chapters"][0].content == "记者林墨开始调查。"
    assert result["chapters"][0].summary == "林墨开始调查。"
    assert client.request_url == "https://api.example.com/v1/responses"
    assert client.request_json["store"] is False
    assert client.request_json["text"]["format"]["type"] == "json_schema"
    assert client.request_json["text"]["format"]["strict"] is True


def test_model_failure_falls_back_to_local_rules(monkeypatch) -> None:
    monkeypatch.setenv("STORYFORGE_LLM_API_KEY", "test-key")
    chapters = [
        Chapter(
            id=f"chapter-{index}",
            title=f"第{index}章",
            content="记者林墨决定调查真相。",
            summary="林墨调查真相",
            keyEvents=["调查真相"],
        )
        for index in range(1, 4)
    ]

    def fail_model_analysis(*args, **kwargs):
        raise LLMAnalysisError("模拟模型失败")

    monkeypatch.setattr(llm_analyzer, "analyze_story_with_model", fail_model_analysis)
    result, mode, error = analyze_story_with_fallback("测试故事", chapters)

    assert result["summary"]
    assert mode == "local-rules-fallback"
    assert error == "模拟模型失败"
