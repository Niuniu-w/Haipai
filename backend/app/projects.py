from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import quote

from .chapter_parser import parse_chapters
from .database import get_db
from .llm_analyzer import analyze_story_with_fallback
from .llm_generator import generate_script_with_fallback
from .llm_polisher import polish_scene_with_fallback
from .models import ProjectRecord
from .script_generator import distribute_scene_counts
from .schemas import (
    Chapter,
    ChapterParseRequest,
    ChapterParseResponse,
    Character,
    Dialogue,
    GenerationChapterState,
    GenerationStatusResponse,
    ProjectData,
    ProjectResponse,
    ProjectSummary,
    Scene,
    ScenePolishRequest,
    ScenePolishResponse,
    ScriptGenerationResponse,
    ScriptValidationResponse,
    StoryAnalysisResponse,
)
from .yaml_export import dump_project_yaml, script_schema, validate_project_script

router = APIRouter(prefix="/api/projects", tags=["项目"])


@router.get("/script-schema", tags=["项目"])
def get_script_schema() -> dict:
    return script_schema()


def get_project_or_404(project_id: str, db: Session) -> ProjectRecord:
    project = db.get(ProjectRecord, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def project_response(project: ProjectRecord) -> ProjectResponse:
    return ProjectResponse.model_validate(project)


def reset_generation(payload: dict) -> None:
    payload.update(
        {
            "scenes": [],
            "generationStatus": "pending",
            "generationMode": "",
            "generationError": "",
            "generationAttempts": 0,
            "generationChapters": [],
        }
    )


def reset_analysis(payload: dict) -> None:
    payload.update(
        {
            "summary": "",
            "genre": "",
            "style": "",
            "era": "",
            "characters": [],
            "relationships": [],
            "analysisStatus": "pending",
            "analysisMode": "",
            "analysisError": "",
            "analysisAttempts": 0,
        }
    )
    reset_generation(payload)


def sync_generation_from_scenes(payload: dict) -> None:
    stored = {
        item.get("chapter_id", ""): item
        for item in payload.get("generationChapters", [])
    }
    states = []
    for chapter in payload.get("chapters", []):
        chapter_id = chapter.get("id", "")
        scene_count = sum(scene.get("chapterId") == chapter_id for scene in payload.get("scenes", []))
        previous = stored.get(chapter_id, {})
        states.append(
            {
                "chapter_id": chapter_id,
                "status": "completed" if scene_count else "pending",
                "mode": previous.get("mode", payload.get("generationMode", "")) if scene_count else "",
                "attempts": int(previous.get("attempts", 0)),
                "error": "",
                "scene_count": scene_count,
            }
        )
    payload["generationChapters"] = states
    payload["generationStatus"] = (
        "completed"
        if states and all(state["status"] == "completed" for state in states)
        else "pending"
    )
    payload["generationError"] = ""
    if not payload.get("scenes"):
        payload["generationMode"] = ""


def check_update_revision(project: ProjectRecord, if_match: str | None) -> int:
    current = int(project.data.get("revision", 0))
    if not if_match:
        raise HTTPException(status_code=428, detail="更新项目必须提供 If-Match 项目版本号")
    try:
        expected = int(if_match)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="If-Match 必须是有效的项目版本号") from exc
    if expected != current:
        raise HTTPException(status_code=409, detail="项目已在其他请求中更新，请重新加载后再保存")
    return current


def chapter_sources(payload: dict) -> list[tuple[str, str, str]]:
    return [
        (chapter.get("id", ""), chapter.get("title", ""), chapter.get("content", ""))
        for chapter in payload.get("chapters", [])
    ]


def target_scenes_for_chapter(payload: dict, chapters: list[Chapter], chapter_id: str) -> int:
    target_total = max(len(chapters), int(payload.get("targetSceneCount", 0) or len(chapters)))
    counts = distribute_scene_counts(len(chapters), target_total)
    return next(
        (counts[index] for index, chapter in enumerate(chapters) if chapter.id == chapter_id),
        1,
    )


def get_chapter_states(payload: dict, chapters: list[Chapter]) -> list[GenerationChapterState]:
    stored = {
        state.chapter_id: state
        for state in (
            GenerationChapterState.model_validate(item)
            for item in payload.get("generationChapters", [])
        )
    }
    scenes = [Scene.model_validate(scene) for scene in payload.get("scenes", [])]
    project_completed = payload.get("generationStatus") == "completed"
    states = []
    for chapter in chapters:
        if chapter.id in stored:
            states.append(stored[chapter.id])
            continue
        scene_count = sum(scene.chapterId == chapter.id for scene in scenes)
        states.append(
            GenerationChapterState(
                chapter_id=chapter.id,
                status="completed" if project_completed and scene_count else "pending",
                mode=payload.get("generationMode", "") if scene_count else "",
                scene_count=scene_count,
            )
        )
    return states


def reindex_scenes(scenes: list[Scene], chapters: list[Chapter]) -> list[Scene]:
    chapter_order = {chapter.id: index for index, chapter in enumerate(chapters)}
    ordered = sorted(enumerate(scenes), key=lambda item: (chapter_order.get(item[1].chapterId, len(chapters)), item[0]))
    return [
        scene.model_copy(
            update={
                "id": f"SC-{scene_index + 1:02d}",
                "dialogues": [
                    Dialogue(
                        id=f"dialogue-{scene_index + 1}-{dialogue_index + 1}",
                        character=dialogue.character,
                        emotion=dialogue.emotion,
                        line=dialogue.line,
                    )
                    for dialogue_index, dialogue in enumerate(scene.dialogues)
                ],
            }
        )
        for scene_index, (_, scene) in enumerate(ordered)
    ]


def aggregate_generation(states: list[GenerationChapterState]) -> tuple[str, str, str]:
    if any(state.status == "failed" for state in states):
        generation_status = "failed"
    elif states and all(state.status == "completed" for state in states):
        generation_status = "completed"
    elif any(state.status in {"running", "completed"} for state in states):
        generation_status = "running"
    else:
        generation_status = "pending"

    modes = {state.mode for state in states if state.mode}
    if "local-rules-fallback" in modes:
        generation_mode = "local-rules-fallback"
    elif len(modes) == 1:
        generation_mode = modes.pop()
    elif modes:
        generation_mode = "mixed"
    else:
        generation_mode = ""
    generation_error = next((state.error for state in states if state.status == "failed" and state.error), "")
    if not generation_error:
        generation_error = next((state.error for state in states if state.error), "")
    return generation_status, generation_mode, generation_error


def save_generation_state(
    project: ProjectRecord,
    db: Session,
    payload: dict,
    states: list[GenerationChapterState],
) -> None:
    generation_status, generation_mode, generation_error = aggregate_generation(states)
    payload.update(
        {
            "generationChapters": [state.model_dump(mode="json") for state in states],
            "generationStatus": generation_status,
            "generationMode": generation_mode,
            "generationError": generation_error,
        }
    )
    project.data = dict(payload)
    db.commit()
    db.refresh(project)


def generation_status_response(project: ProjectRecord) -> GenerationStatusResponse:
    payload = dict(project.data)
    chapters = [Chapter.model_validate(chapter) for chapter in payload.get("chapters", [])]
    states = get_chapter_states(payload, chapters)
    return GenerationStatusResponse(
        status=payload.get("generationStatus", "pending"),
        mode=payload.get("generationMode", ""),
        attempts=int(payload.get("generationAttempts", 0)),
        error=payload.get("generationError", ""),
        scene_count=len(payload.get("scenes", [])),
        chapter_statuses=states,
    )


def script_generation_response(project: ProjectRecord) -> ScriptGenerationResponse:
    payload = dict(project.data)
    chapters = [Chapter.model_validate(chapter) for chapter in payload.get("chapters", [])]
    scenes = [Scene.model_validate(scene) for scene in payload.get("scenes", [])]
    return ScriptGenerationResponse(
        scenes=scenes,
        scene_count=len(scenes),
        generation_status=payload.get("generationStatus", "pending"),
        generation_mode=payload.get("generationMode", ""),
        generation_attempts=int(payload.get("generationAttempts", 0)),
        generation_error=payload.get("generationError", ""),
        chapter_statuses=get_chapter_states(payload, chapters),
    )


def initialize_generation(project: ProjectRecord, db: Session) -> GenerationStatusResponse:
    payload = dict(project.data)
    chapters = [Chapter.model_validate(chapter) for chapter in payload.get("chapters", [])]
    if len(chapters) < 3:
        raise HTTPException(status_code=409, detail="至少需要 3 个章节才能生成剧本")
    states = [GenerationChapterState(chapter_id=chapter.id) for chapter in chapters]
    payload.update(
        {
            "scenes": [],
            "generationStatus": "pending",
            "generationMode": "",
            "generationError": "",
            "generationAttempts": int(payload.get("generationAttempts", 0)) + 1,
            "generationChapters": [state.model_dump(mode="json") for state in states],
        }
    )
    project.data = dict(payload)
    db.commit()
    db.refresh(project)
    return generation_status_response(project)


def generate_chapter(project: ProjectRecord, chapter_id: str, db: Session) -> ScriptGenerationResponse:
    payload = dict(project.data)
    chapters = [Chapter.model_validate(chapter) for chapter in payload.get("chapters", [])]
    characters = [Character.model_validate(character) for character in payload.get("characters", [])]
    chapter = next((item for item in chapters if item.id == chapter_id), None)
    if chapter is None:
        raise HTTPException(status_code=404, detail="章节不存在")

    states = get_chapter_states(payload, chapters)
    chapter_state = next(state for state in states if state.chapter_id == chapter_id)
    chapter_state.status = "running"
    chapter_state.attempts += 1
    chapter_state.error = ""
    payload["generationAttempts"] = max(1, int(payload.get("generationAttempts", 0)))
    save_generation_state(project, db, payload, states)

    try:
        generated_scenes, generation_mode, generation_error = generate_script_with_fallback(
            title=project.title,
            summary=payload.get("summary", ""),
            genre=payload.get("genre", ""),
            style=payload.get("style", ""),
            adaptation_mode=payload.get("adaptationMode", "忠于原著"),
            script_type=payload.get("scriptType", "电影"),
            chapters=[chapter],
            characters=characters,
            dialogue_density=payload.get("dialogueDensity", "均衡"),
            target_scene_count=target_scenes_for_chapter(payload, chapters, chapter_id),
        )
        existing_scenes = [
            Scene.model_validate(scene)
            for scene in payload.get("scenes", [])
            if scene.get("chapterId") != chapter_id
        ]
        scenes = reindex_scenes(existing_scenes + generated_scenes, chapters)
        chapter_state.status = "completed"
        chapter_state.mode = generation_mode
        chapter_state.error = generation_error
        chapter_state.scene_count = sum(scene.chapterId == chapter_id for scene in scenes)
        payload["scenes"] = [scene.model_dump(mode="json") for scene in scenes]
        save_generation_state(project, db, payload, states)
        return script_generation_response(project)
    except Exception as exc:
        chapter_state.status = "failed"
        chapter_state.error = "章节剧本生成失败"
        chapter_state.scene_count = 0
        save_generation_state(project, db, payload, states)
        raise HTTPException(status_code=500, detail="章节剧本生成失败") from exc


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectData, db: Session = Depends(get_db)) -> ProjectResponse:
    payload = data.model_dump(mode="json", by_alias=True)
    project = ProjectRecord(title=data.title, data=payload)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project_response(project)


@router.get("", response_model=list[ProjectSummary])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectSummary]:
    projects = db.scalars(select(ProjectRecord).order_by(ProjectRecord.updated_at.desc())).all()
    return [
        ProjectSummary(
            id=project.id,
            title=project.title,
            chapter_count=len(project.data.get("chapters", [])),
            scene_count=len(project.data.get("scenes", [])),
            updated_at=project.updated_at,
        )
        for project in projects
    ]


@router.post("/{project_id}/parse-chapters", response_model=ChapterParseResponse)
def parse_project_chapters(
    project_id: str,
    request: ChapterParseRequest,
    db: Session = Depends(get_db),
) -> ChapterParseResponse:
    project = get_project_or_404(project_id, db)
    chapters = parse_chapters(request.raw_text)
    payload = dict(project.data)
    payload["rawText"] = request.raw_text
    payload["chapters"] = [chapter.model_dump(mode="json") for chapter in chapters]
    reset_analysis(payload)
    project.data = payload
    db.commit()
    db.refresh(project)
    return ChapterParseResponse(
        chapters=chapters,
        chapter_count=len(chapters),
        valid=len(chapters) >= 3,
    )


@router.post("/{project_id}/analyze", response_model=StoryAnalysisResponse)
def analyze_project(project_id: str, db: Session = Depends(get_db)) -> StoryAnalysisResponse:
    project = get_project_or_404(project_id, db)
    chapters = [Chapter.model_validate(chapter) for chapter in project.data.get("chapters", [])]
    if len(chapters) < 3:
        raise HTTPException(status_code=409, detail="至少需要 3 个章节才能开始故事分析")

    payload = dict(project.data)
    attempts = int(payload.get("analysisAttempts", 0)) + 1
    payload.update({"analysisStatus": "running", "analysisError": "", "analysisAttempts": attempts})

    try:
        result, analysis_mode, analysis_error = analyze_story_with_fallback(project.title, chapters)
        payload.update(
            {
                "summary": result["summary"],
                "genre": result["genre"],
                "era": result["era"],
                "style": result["style"],
                "characters": [character.model_dump(mode="json") for character in result["characters"]],
                "relationships": [
                    relationship.model_dump(mode="json", by_alias=True) for relationship in result["relationships"]
                ],
                "chapters": [chapter.model_dump(mode="json") for chapter in result["chapters"]],
                "analysisStatus": "completed",
                "analysisMode": analysis_mode,
                "analysisError": analysis_error,
            }
        )
        reset_generation(payload)
        project.data = dict(payload)
        db.commit()
        db.refresh(project)
        return StoryAnalysisResponse(
            **result,
            analysis_status="completed",
            analysis_mode=analysis_mode,
            analysis_attempts=attempts,
            analysis_error=analysis_error,
        )
    except Exception as exc:
        payload.update({"analysisStatus": "failed", "analysisError": "故事分析失败"})
        project.data = dict(payload)
        db.commit()
        raise HTTPException(status_code=500, detail="故事分析失败") from exc


@router.post("/{project_id}/generate", response_model=ScriptGenerationResponse)
def generate_project_script(project_id: str, db: Session = Depends(get_db)) -> ScriptGenerationResponse:
    project = get_project_or_404(project_id, db)
    chapters = [Chapter.model_validate(chapter) for chapter in project.data.get("chapters", [])]
    initialize_generation(project, db)
    for chapter in chapters:
        generate_chapter(project, chapter.id, db)
    return script_generation_response(project)


@router.post("/{project_id}/generation/start", response_model=GenerationStatusResponse)
def start_project_generation(project_id: str, db: Session = Depends(get_db)) -> GenerationStatusResponse:
    return initialize_generation(get_project_or_404(project_id, db), db)


@router.post("/{project_id}/chapters/{chapter_id}/generate", response_model=ScriptGenerationResponse)
def generate_project_chapter(
    project_id: str,
    chapter_id: str,
    db: Session = Depends(get_db),
) -> ScriptGenerationResponse:
    return generate_chapter(get_project_or_404(project_id, db), chapter_id, db)


@router.post("/{project_id}/scenes/{scene_id}/polish", response_model=ScenePolishResponse)
def polish_project_scene(
    project_id: str,
    scene_id: str,
    request: ScenePolishRequest,
    db: Session = Depends(get_db),
) -> ScenePolishResponse:
    project = get_project_or_404(project_id, db)
    payload = dict(project.data)
    scenes = [Scene.model_validate(scene) for scene in payload.get("scenes", [])]
    scene_index = next((index for index, scene in enumerate(scenes) if scene.id == scene_id), None)
    if scene_index is None:
        raise HTTPException(status_code=404, detail="场景不存在")
    characters = [Character.model_validate(character) for character in payload.get("characters", [])]
    polished, mode, error = polish_scene_with_fallback(scenes[scene_index], request.instruction, characters)
    scenes[scene_index] = polished
    payload["scenes"] = [scene.model_dump(mode="json") for scene in scenes]
    project.data = payload
    db.commit()
    db.refresh(project)
    return ScenePolishResponse(scene=polished, mode=mode, error=error)


@router.get("/{project_id}/generation-status", response_model=GenerationStatusResponse)
def get_generation_status(project_id: str, db: Session = Depends(get_db)) -> GenerationStatusResponse:
    return generation_status_response(get_project_or_404(project_id, db))


@router.get("/{project_id}/validate-script", response_model=ScriptValidationResponse)
def validate_project_yaml(project_id: str, db: Session = Depends(get_db)) -> ScriptValidationResponse:
    data = ProjectData.model_validate(get_project_or_404(project_id, db).data)
    errors = validate_project_script(data)
    return ScriptValidationResponse(valid=not errors, errors=errors, scene_count=len(data.scenes))


@router.get("/{project_id}/export/yaml")
def export_project_yaml(project_id: str, db: Session = Depends(get_db)) -> Response:
    data = ProjectData.model_validate(get_project_or_404(project_id, db).data)
    errors = validate_project_script(data)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "剧本结构校验失败", "errors": errors})
    filename = "".join(character if character not in r'\/:*?"<>|' else "_" for character in data.title) or "storyforge"
    return Response(
        content=dump_project_yaml(data),
        media_type="application/yaml; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}.yaml"},
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectResponse:
    return project_response(get_project_or_404(project_id, db))


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    data: ProjectData,
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> ProjectResponse:
    project = get_project_or_404(project_id, db)
    revision = check_update_revision(project, if_match)
    previous_payload = dict(project.data)
    payload = data.model_dump(mode="json", by_alias=True)
    if chapter_sources(previous_payload) != chapter_sources(payload):
        reset_analysis(payload)
    elif previous_payload.get("scenes", []) != payload.get("scenes", []):
        sync_generation_from_scenes(payload)
    payload["revision"] = revision + 1
    project.title = data.title
    project.data = payload
    db.commit()
    db.refresh(project)
    return project_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> Response:
    project = get_project_or_404(project_id, db)
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
