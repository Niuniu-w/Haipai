import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import backend.app.projects as projects
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.script_generator import build_local_scenes


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def disable_real_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STORYFORGE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def project_data() -> dict:
    return {
        "title": "测试故事",
        "filename": "test.txt",
        "rawText": "第一章 开始",
        "genre": "悬疑",
        "style": "",
        "era": "",
        "summary": "",
        "adaptationMode": "忠于原著",
        "scriptType": "电影",
        "dialogueDensity": "均衡",
        "targetSceneCount": 0,
        "chapters": [],
        "characters": [],
        "relationships": [],
        "scenes": [],
        "updatedAt": "刚刚",
        "revision": 0,
        "analysisStatus": "pending",
        "analysisMode": "",
        "analysisError": "",
        "analysisAttempts": 0,
        "generationStatus": "pending",
        "generationMode": "",
        "generationError": "",
        "generationAttempts": 0,
        "generationChapters": [],
    }


@pytest.fixture
async def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_project_crud(client: AsyncClient, project_data: dict) -> None:
    create_response = await client.post("/api/projects", json=project_data)
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]
    revision = create_response.json()["data"]["revision"]

    list_response = await client.get("/api/projects")
    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "测试故事"

    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"] == project_data

    updated_data = {**project_data, "title": "更新后的故事"}
    update_response = await client.put(
        f"/api/projects/{project_id}",
        json=updated_data,
        headers={"If-Match": str(revision)},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["title"] == "更新后的故事"

    delete_response = await client.delete(f"/api/projects/{project_id}")
    assert delete_response.status_code == 204
    assert (await client.get(f"/api/projects/{project_id}")).status_code == 404


@pytest.mark.anyio
async def test_project_validation(client: AsyncClient, project_data: dict) -> None:
    invalid_data = {**project_data, "title": ""}
    response = await client.post("/api/projects", json=invalid_data)
    assert response.status_code == 422


@pytest.mark.anyio
async def test_parse_chapters_saves_result(client: AsyncClient, project_data: dict) -> None:
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    raw_text = """第一章 开始

第一章的第一句话。第一章的第二句话。

第二章 继续

第二章内容。

Chapter 3 Ending

The ending."""

    response = await client.post(
        f"/api/projects/{project_id}/parse-chapters",
        json={"raw_text": raw_text},
    )

    assert response.status_code == 200
    assert response.json()["chapter_count"] == 3
    assert response.json()["valid"] is True
    assert response.json()["chapters"][0]["summary"] == "第一章的第一句话。第一章的第二句话"

    saved_project = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    assert saved_project["rawText"] == raw_text
    assert len(saved_project["chapters"]) == 3


@pytest.mark.anyio
async def test_parse_chapters_invalidates_previous_analysis_and_generation(
    client: AsyncClient,
    project_data: dict,
) -> None:
    stale_project = {
        **project_data,
        "summary": "旧概要",
        "genre": "旧题材",
        "style": "旧风格",
        "era": "旧时代",
        "characters": [
            {
                "id": "char-1",
                "name": "旧人物",
                "role": "旧角色",
                "description": "旧简介",
                "color": "#000000",
            }
        ],
        "relationships": [{"from": "旧人物", "to": "另一个人", "relation": "旧关系"}],
        "scenes": [
            {
                "id": "SC-01",
                "chapterId": "chapter-old",
                "sourceChapter": "旧章节",
                "title": "旧场景",
                "location": "旧地点",
                "time": "旧时间",
                "atmosphere": "旧氛围",
                "characters": ["旧人物"],
                "actions": ["旧动作"],
                "dialogues": [],
                "sourceSummary": "旧来源摘要",
            }
        ],
        "analysisStatus": "completed",
        "analysisMode": "local-rules",
        "analysisAttempts": 2,
        "generationStatus": "completed",
        "generationMode": "local-rules",
        "generationAttempts": 3,
        "generationChapters": [
            {
                "chapter_id": "chapter-old",
                "status": "completed",
                "mode": "local-rules",
                "attempts": 1,
                "error": "",
                "scene_count": 1,
            }
        ],
    }
    project_id = (await client.post("/api/projects", json=stale_project)).json()["id"]

    await client.post(
        f"/api/projects/{project_id}/parse-chapters",
        json={"raw_text": "第一章 新开始\n新内容。\n\n第二章 新继续\n新内容。\n\n第三章 新结尾\n新内容。"},
    )

    saved_project = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    assert saved_project["summary"] == ""
    assert saved_project["genre"] == ""
    assert saved_project["style"] == ""
    assert saved_project["era"] == ""
    assert saved_project["characters"] == []
    assert saved_project["relationships"] == []
    assert saved_project["analysisStatus"] == "pending"
    assert saved_project["analysisAttempts"] == 0
    assert saved_project["scenes"] == []
    assert saved_project["generationStatus"] == "pending"
    assert saved_project["generationAttempts"] == 0
    assert saved_project["generationChapters"] == []


@pytest.mark.anyio
async def test_updating_chapter_source_invalidates_previous_analysis_and_generation(
    client: AsyncClient,
    project_data: dict,
) -> None:
    raw_text = """第一章 开始
林墨走进咖啡馆。

第二章 继续
苏禾在档案室找到线索。

第三章 结尾
陈望在桥下说出真相。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")
    await client.post(f"/api/projects/{project_id}/generate")
    current = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    current["chapters"][0]["content"] += " 新增正文。"

    response = await client.put(
        f"/api/projects/{project_id}",
        json=current,
        headers={"If-Match": str(current["revision"])},
    )

    assert response.status_code == 200
    saved_project = response.json()["data"]
    assert saved_project["chapters"][0]["content"].endswith("新增正文。")
    assert saved_project["summary"] == ""
    assert saved_project["characters"] == []
    assert saved_project["relationships"] == []
    assert saved_project["analysisStatus"] == "pending"
    assert saved_project["scenes"] == []
    assert saved_project["generationStatus"] == "pending"
    assert saved_project["generationChapters"] == []


@pytest.mark.anyio
async def test_updating_chapter_analysis_metadata_does_not_invalidate_results(
    client: AsyncClient,
    project_data: dict,
) -> None:
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    current = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    current["summary"] = "保留概要"
    current["chapters"] = [
        {
            "id": "chapter-1",
            "title": "第一章",
            "content": "正文",
            "summary": "更新后的章节概要",
            "keyEvents": ["更新后的事件"],
        }
    ]
    first_update = await client.put(
        f"/api/projects/{project_id}",
        json=current,
        headers={"If-Match": str(current["revision"])},
    )
    first_data = first_update.json()["data"]
    first_data["summary"] = "分析完成概要"
    first_data["analysisStatus"] = "completed"
    first_data["chapters"][0]["summary"] = "再次更新章节概要"

    response = await client.put(
        f"/api/projects/{project_id}",
        json=first_data,
        headers={"If-Match": str(first_data["revision"])},
    )

    assert response.status_code == 200
    assert response.json()["data"]["summary"] == "分析完成概要"
    assert response.json()["data"]["analysisStatus"] == "completed"


@pytest.mark.anyio
async def test_parse_chapters_requires_at_least_three(client: AsyncClient, project_data: dict) -> None:
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    response = await client.post(
        f"/api/projects/{project_id}/parse-chapters",
        json={"raw_text": "第一章 唯一章节\n只有一章。"},
    )

    assert response.status_code == 200
    assert response.json()["chapter_count"] == 1
    assert response.json()["valid"] is False


@pytest.mark.anyio
async def test_analyze_project_saves_story_analysis(client: AsyncClient, project_data: dict) -> None:
    raw_text = """第一章 雨夜
记者林墨收到一封匿名信。老板周岚警告林墨不要调查。

第二章 线索
实习生苏禾发现失踪的证据。林墨决定继续调查真相。

第三章 对峙
林墨约周岚见面。刑警陈望出现并告诉林墨事故的秘密。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})

    response = await client.post(f"/api/projects/{project_id}/analyze")

    assert response.status_code == 200
    assert response.json()["analysis_status"] == "completed"
    assert response.json()["analysis_mode"] == "local-rules"
    assert response.json()["analysis_attempts"] == 1
    assert response.json()["genre"] == "悬疑"
    assert any(character["name"] == "林墨" for character in response.json()["characters"])
    assert all(character["name"] not in {"林墨决定", "周岚警告"} for character in response.json()["characters"])

    saved_project = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    assert saved_project["analysisStatus"] == "completed"
    assert saved_project["analysisMode"] == "local-rules"
    assert saved_project["analysisAttempts"] == 1
    assert saved_project["summary"]


@pytest.mark.anyio
async def test_analyze_project_requires_three_chapters(client: AsyncClient, project_data: dict) -> None:
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    response = await client.post(f"/api/projects/{project_id}/analyze")

    assert response.status_code == 409


@pytest.mark.anyio
async def test_generate_project_saves_scenes(client: AsyncClient, project_data: dict) -> None:
    raw_text = """第一章 雨夜
记者林墨走进咖啡馆。他收到匿名信。

第二章 线索
实习生苏禾在档案室发现证据。林墨决定调查。

第三章 对峙
刑警陈望在桥下出现。林墨说：“真相不会消失。”"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")

    response = await client.post(f"/api/projects/{project_id}/generate")

    assert response.status_code == 200
    assert response.json()["generation_status"] == "completed"
    assert response.json()["generation_mode"] == "local-rules"
    assert response.json()["scene_count"] == 3
    assert response.json()["scenes"][0]["chapterId"] == "chapter-1"
    assert response.json()["scenes"][2]["dialogues"][0]["line"] == "真相不会消失。"
    assert response.json()["scenes"][2]["dialogues"][0]["character"] == "林墨"

    saved_project = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    assert saved_project["generationStatus"] == "completed"
    assert saved_project["generationAttempts"] == 1
    assert len(saved_project["scenes"]) == 3

    status_response = await client.get(f"/api/projects/{project_id}/generation-status")
    assert status_response.json()["scene_count"] == 3
    assert status_response.json()["status"] == "completed"


@pytest.mark.anyio
async def test_generate_project_requires_three_chapters(client: AsyncClient, project_data: dict) -> None:
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    response = await client.post(f"/api/projects/{project_id}/generate")

    assert response.status_code == 409


@pytest.mark.anyio
async def test_generation_respects_target_scene_count(
    client: AsyncClient,
    project_data: dict,
) -> None:
    raw_text = """第一章 开始
林墨走进咖啡馆。他坐到窗边。

第二章 继续
苏禾找到线索。她赶往桥下。

第三章 结尾
陈望说出真相。众人离开。"""
    configured = {**project_data, "targetSceneCount": 5, "dialogueDensity": "密集"}
    project_id = (await client.post("/api/projects", json=configured)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")

    response = await client.post(f"/api/projects/{project_id}/generate")

    assert response.status_code == 200
    assert response.json()["scene_count"] == 5
    assert [item["scene_count"] for item in response.json()["chapter_statuses"]] == [2, 2, 1]


@pytest.mark.anyio
async def test_generation_runs_and_persists_one_chapter_at_a_time(
    client: AsyncClient,
    project_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_text = """第一章 开始
林墨走进咖啡馆。

第二章 继续
苏禾在档案室找到线索。

第三章 结尾
陈望在桥下说出真相。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")
    generated_chapter_ids: list[list[str]] = []

    def record_generation(*args, **kwargs):
        chapters = kwargs["chapters"]
        generated_chapter_ids.append([chapter.id for chapter in chapters])
        return (
            build_local_scenes(chapters, kwargs["characters"], kwargs["genre"], kwargs["style"]),
            "local-rules",
            "",
        )

    monkeypatch.setattr(projects, "generate_script_with_fallback", record_generation)

    start_response = await client.post(f"/api/projects/{project_id}/generation/start")
    assert start_response.status_code == 200
    assert [item["status"] for item in start_response.json()["chapter_statuses"]] == ["pending"] * 3

    first_response = await client.post(f"/api/projects/{project_id}/chapters/chapter-1/generate")
    assert first_response.status_code == 200
    assert first_response.json()["generation_status"] == "running"
    assert first_response.json()["scene_count"] == 1
    assert [item["status"] for item in first_response.json()["chapter_statuses"]] == [
        "completed",
        "pending",
        "pending",
    ]

    saved_project = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    assert len(saved_project["scenes"]) == 1
    assert saved_project["generationChapters"][0]["status"] == "completed"

    await client.post(f"/api/projects/{project_id}/chapters/chapter-2/generate")
    final_response = await client.post(f"/api/projects/{project_id}/chapters/chapter-3/generate")
    assert final_response.json()["generation_status"] == "completed"
    assert final_response.json()["scene_count"] == 3
    assert generated_chapter_ids == [["chapter-1"], ["chapter-2"], ["chapter-3"]]


@pytest.mark.anyio
async def test_compatibility_generate_endpoint_never_sends_multiple_chapters_to_model(
    client: AsyncClient,
    project_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_text = """第一章 开始
林墨走进咖啡馆。

第二章 继续
苏禾在档案室找到线索。

第三章 结尾
陈望在桥下说出真相。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")
    generated_chapter_ids: list[list[str]] = []

    def record_generation(*args, **kwargs):
        chapters = kwargs["chapters"]
        generated_chapter_ids.append([chapter.id for chapter in chapters])
        return (
            build_local_scenes(chapters, kwargs["characters"], kwargs["genre"], kwargs["style"]),
            "local-rules",
            "",
        )

    monkeypatch.setattr(projects, "generate_script_with_fallback", record_generation)

    response = await client.post(f"/api/projects/{project_id}/generate")

    assert response.status_code == 200
    assert response.json()["generation_status"] == "completed"
    assert generated_chapter_ids == [["chapter-1"], ["chapter-2"], ["chapter-3"]]


@pytest.mark.anyio
async def test_failed_chapter_can_retry_without_regenerating_other_chapters(
    client: AsyncClient,
    project_data: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_text = """第一章 开始
林墨走进咖啡馆。

第二章 继续
苏禾在档案室找到线索。

第三章 结尾
陈望在桥下说出真相。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")
    await client.post(f"/api/projects/{project_id}/generation/start")
    calls: list[str] = []

    def fail_second_chapter_once(*args, **kwargs):
        chapter = kwargs["chapters"][0]
        calls.append(chapter.id)
        if chapter.id == "chapter-2" and calls.count("chapter-2") == 1:
            raise RuntimeError("模拟单章失败")
        return (
            build_local_scenes(kwargs["chapters"], kwargs["characters"], kwargs["genre"], kwargs["style"]),
            "local-rules",
            "",
        )

    monkeypatch.setattr(projects, "generate_script_with_fallback", fail_second_chapter_once)

    await client.post(f"/api/projects/{project_id}/chapters/chapter-1/generate")
    first_chapter_scenes = [
        scene
        for scene in (await client.get(f"/api/projects/{project_id}")).json()["data"]["scenes"]
        if scene["chapterId"] == "chapter-1"
    ]

    failed_response = await client.post(f"/api/projects/{project_id}/chapters/chapter-2/generate")
    assert failed_response.status_code == 500
    status_response = await client.get(f"/api/projects/{project_id}/generation-status")
    assert status_response.json()["status"] == "failed"
    assert status_response.json()["chapter_statuses"][1]["status"] == "failed"

    retry_response = await client.post(f"/api/projects/{project_id}/chapters/chapter-2/generate")
    assert retry_response.status_code == 200
    assert retry_response.json()["chapter_statuses"][1]["status"] == "completed"
    assert retry_response.json()["chapter_statuses"][1]["attempts"] == 2
    assert calls == ["chapter-1", "chapter-2", "chapter-2"]
    assert [
        scene for scene in retry_response.json()["scenes"] if scene["chapterId"] == "chapter-1"
    ] == first_chapter_scenes


@pytest.mark.anyio
async def test_validate_and_export_yaml(client: AsyncClient, project_data: dict) -> None:
    raw_text = """第一章 开始
林墨走进咖啡馆。

第二章 继续
苏禾在档案室找到线索。

第三章 结尾
陈望在桥下说出真相。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")
    await client.post(f"/api/projects/{project_id}/generate")

    validation_response = await client.get(f"/api/projects/{project_id}/validate-script")
    assert validation_response.status_code == 200
    assert validation_response.json() == {"valid": True, "errors": [], "scene_count": 3}

    export_response = await client.get(f"/api/projects/{project_id}/export/yaml")
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/yaml")
    exported = yaml.safe_load(export_response.text)
    assert exported["schema_version"] == "storyforge-script/v1"
    assert exported["title"] == "测试故事"
    assert len(exported["chapters"]) == 3
    assert len(exported["scenes"]) == 3
    assert exported["scenes"][0]["source_chapter_id"] == "chapter-1"
    assert exported["scenes"][0]["source_chapter"] == "第一章 开始"


@pytest.mark.anyio
async def test_invalid_script_cannot_export_yaml(client: AsyncClient, project_data: dict) -> None:
    invalid_scene = {
        "id": "SC-01",
        "chapterId": "missing-chapter",
        "sourceChapter": "不存在的章节",
        "title": "",
        "location": "",
        "time": "",
        "atmosphere": "",
        "characters": ["不存在的人物"],
        "actions": [],
        "dialogues": [
            {
                "id": "dialogue-1",
                "character": "对白人物",
                "emotion": "",
                "line": "",
            }
        ],
        "sourceSummary": "",
    }
    project_id = (
        await client.post("/api/projects", json={**project_data, "scenes": [invalid_scene]})
    ).json()["id"]

    validation_response = await client.get(f"/api/projects/{project_id}/validate-script")
    assert validation_response.status_code == 200
    assert validation_response.json()["valid"] is False
    assert "SC-01：来源章节不存在" in validation_response.json()["errors"]

    export_response = await client.get(f"/api/projects/{project_id}/export/yaml")
    assert export_response.status_code == 422
    assert export_response.json()["detail"]["message"] == "剧本结构校验失败"


@pytest.mark.anyio
async def test_script_schema_is_versioned(client: AsyncClient) -> None:
    response = await client.get("/api/projects/script-schema")

    assert response.status_code == 200
    assert response.json()["properties"]["schema_version"]["const"] == "storyforge-script/v1"


@pytest.mark.anyio
async def test_validation_rejects_duplicate_chapters_and_chapters_without_scenes(
    client: AsyncClient,
    project_data: dict,
) -> None:
    chapters = [
        {
            "id": "chapter-1",
            "title": "第一章",
            "content": "正文一",
            "summary": "概要一",
            "keyEvents": ["事件一"],
        },
        {
            "id": "chapter-1",
            "title": "第二章",
            "content": "正文二",
            "summary": "概要二",
            "keyEvents": ["事件二"],
        },
    ]
    scene = {
        "id": "SC-01",
        "chapterId": "chapter-1",
        "sourceChapter": "第一章",
        "title": "场景",
        "location": "地点",
        "time": "日",
        "atmosphere": "平静",
        "characters": [],
        "actions": ["动作"],
        "dialogues": [],
        "sourceSummary": "概要",
    }
    project_id = (
        await client.post("/api/projects", json={**project_data, "chapters": chapters, "scenes": [scene]})
    ).json()["id"]

    errors = (await client.get(f"/api/projects/{project_id}/validate-script")).json()["errors"]

    assert "章节 ID 重复：chapter-1" in errors


@pytest.mark.anyio
async def test_manual_scene_changes_recalculate_generation_status(
    client: AsyncClient,
    project_data: dict,
) -> None:
    raw_text = """第一章 开始
第一章正文。

第二章 继续
第二章正文。

第三章 结尾
第三章正文。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")
    await client.post(f"/api/projects/{project_id}/generate")
    current_response = await client.get(f"/api/projects/{project_id}")
    current = current_response.json()["data"]
    current["scenes"] = [
        scene for scene in current["scenes"] if scene["chapterId"] != "chapter-2"
    ]

    response = await client.put(
        f"/api/projects/{project_id}",
        json=current,
        headers={"If-Match": str(current_response.json()["data"]["revision"])},
    )

    assert response.status_code == 200
    saved = response.json()["data"]
    assert saved["generationStatus"] == "pending"
    assert saved["generationChapters"][1]["status"] == "pending"
    assert saved["generationChapters"][1]["scene_count"] == 0


@pytest.mark.anyio
async def test_update_rejects_stale_revision(client: AsyncClient, project_data: dict) -> None:
    created = (await client.post("/api/projects", json=project_data)).json()
    first_update = await client.put(
        f"/api/projects/{created['id']}",
        json={**project_data, "title": "第一次更新"},
        headers={"If-Match": str(created["data"]["revision"])},
    )

    stale_update = await client.put(
        f"/api/projects/{created['id']}",
        json={**project_data, "title": "过期更新"},
        headers={"If-Match": str(created["data"]["revision"])},
    )

    assert first_update.status_code == 200
    assert stale_update.status_code == 409

    missing_revision = await client.put(
        f"/api/projects/{created['id']}",
        json={**project_data, "title": "无版本更新"},
    )
    assert missing_revision.status_code == 428


@pytest.mark.anyio
async def test_scene_polish_uses_backend_fallback_and_persists(
    client: AsyncClient,
    project_data: dict,
) -> None:
    raw_text = """第一章 开始
林墨走进咖啡馆。

第二章 继续
林墨找到线索。

第三章 结尾
林墨说出真相。"""
    project_id = (await client.post("/api/projects", json=project_data)).json()["id"]
    await client.post(f"/api/projects/{project_id}/parse-chapters", json={"raw_text": raw_text})
    await client.post(f"/api/projects/{project_id}/analyze")
    generated = await client.post(f"/api/projects/{project_id}/generate")
    scene_id = generated.json()["scenes"][0]["id"]

    response = await client.post(
        f"/api/projects/{project_id}/scenes/{scene_id}/polish",
        json={"instruction": "改成夜晚并增强冲突"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "local-rules"
    assert response.json()["scene"]["time"] == "夜"
    saved = (await client.get(f"/api/projects/{project_id}")).json()["data"]
    assert saved["scenes"][0]["time"] == "夜"
