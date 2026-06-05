import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app


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
        "chapters": [],
        "characters": [],
        "relationships": [],
        "scenes": [],
        "updatedAt": "刚刚",
        "analysisStatus": "pending",
        "analysisMode": "",
        "analysisError": "",
        "analysisAttempts": 0,
        "generationStatus": "pending",
        "generationMode": "",
        "generationError": "",
        "generationAttempts": 0,
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

    list_response = await client.get("/api/projects")
    assert list_response.status_code == 200
    assert list_response.json()[0]["title"] == "测试故事"

    get_response = await client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"] == project_data

    updated_data = {**project_data, "title": "更新后的故事"}
    update_response = await client.put(f"/api/projects/{project_id}", json=updated_data)
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
