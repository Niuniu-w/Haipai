import json

from backend.app.llm_polisher import polish_scene_with_model
from backend.app.schemas import Character, Scene, SceneContentItem
from backend.app.settings import LLMSettings


class FakeResponse:
    def __init__(self, data: dict) -> None:
        self.data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.data


class FakeClient:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.request_json: dict = {}

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.request_json = kwargs["json"]
        return FakeResponse({"output_text": json.dumps(self.output, ensure_ascii=False)})


def test_model_scene_polish_uses_structured_output_and_preserves_identity() -> None:
    scene = Scene(
        id="SC-01",
        chapterId="chapter-1",
        sourceChapter="第一章",
        title="原场景",
        location="咖啡馆",
        time="日",
        atmosphere="平静",
        characters=["林墨"],
        content=[
            SceneContentItem(id="c-1", type="action", action="林墨走进咖啡馆。"),
            SceneContentItem(
                id="c-2",
                type="dialogue",
                action="林墨向店员点头。",
                character="林墨",
                emotion="平静",
                line="你好。",
            ),
        ],
        sourceSummary="林墨进入咖啡馆。",
    )
    output = {
        "title": "夜谈",
        "location": "咖啡馆",
        "time": "夜",
        "atmosphere": "紧张",
        "characters": ["林墨"],
        "content": [
            {"type": "action", "action": "林墨关上门。"},
            {
                "type": "dialogue",
                "action": "林墨背靠门板，警惕地望向黑暗。",
                "character": "林墨",
                "emotion": "警惕",
                "line": "谁在那里？",
            },
        ],
        "sourceSummary": "林墨进入咖啡馆。",
    }
    client = FakeClient(output)
    settings = LLMSettings(
        api_key="test-key",
        base_url="https://api.example.com/v1",
        model="test-model",
        timeout_seconds=10,
        max_input_chars=10000,
    )

    result = polish_scene_with_model(
        scene,
        "改成夜晚并增强冲突",
        [Character(id="c-1", name="林墨", role="记者", description="调查者", color="#000")],
        settings=settings,
        client=client,
    )

    assert result.id == "SC-01"
    assert result.chapterId == "chapter-1"
    assert result.time == "夜"
    assert result.content[1].id == "SC-01-content-2"
    assert result.content[1].action == "林墨背靠门板，警惕地望向黑暗。"
    assert client.request_json["text"]["format"]["type"] == "json_schema"
