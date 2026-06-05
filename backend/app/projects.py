from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .chapter_parser import parse_chapters
from .database import get_db
from .llm_analyzer import analyze_story_with_fallback
from .llm_generator import generate_script_with_fallback
from .models import ProjectRecord
from .schemas import (
    Chapter,
    ChapterParseRequest,
    ChapterParseResponse,
    Character,
    GenerationStatusResponse,
    ProjectData,
    ProjectResponse,
    ProjectSummary,
    ScriptGenerationResponse,
    StoryAnalysisResponse,
)

router = APIRouter(prefix="/api/projects", tags=["项目"])


def get_project_or_404(project_id: str, db: Session) -> ProjectRecord:
    project = db.get(ProjectRecord, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def project_response(project: ProjectRecord) -> ProjectResponse:
    return ProjectResponse.model_validate(project)


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
    payload["analysisStatus"] = "pending"
    payload["analysisMode"] = ""
    payload["analysisError"] = ""
    payload["analysisAttempts"] = 0
    payload["scenes"] = []
    payload["generationStatus"] = "pending"
    payload["generationMode"] = ""
    payload["generationError"] = ""
    payload["generationAttempts"] = 0
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
                "scenes": [],
                "generationStatus": "pending",
                "generationMode": "",
                "generationError": "",
                "generationAttempts": 0,
            }
        )
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
    characters = [Character.model_validate(character) for character in project.data.get("characters", [])]
    if len(chapters) < 3:
        raise HTTPException(status_code=409, detail="至少需要 3 个章节才能生成剧本")

    payload = dict(project.data)
    attempts = int(payload.get("generationAttempts", 0)) + 1
    try:
        scenes, generation_mode, generation_error = generate_script_with_fallback(
            title=project.title,
            summary=payload.get("summary", ""),
            genre=payload.get("genre", ""),
            style=payload.get("style", ""),
            adaptation_mode=payload.get("adaptationMode", "忠于原著"),
            script_type=payload.get("scriptType", "电影"),
            chapters=chapters,
            characters=characters,
        )
        payload.update(
            {
                "scenes": [scene.model_dump(mode="json") for scene in scenes],
                "generationStatus": "completed",
                "generationMode": generation_mode,
                "generationError": generation_error,
                "generationAttempts": attempts,
            }
        )
        project.data = dict(payload)
        db.commit()
        db.refresh(project)
        return ScriptGenerationResponse(
            scenes=scenes,
            scene_count=len(scenes),
            generation_status="completed",
            generation_mode=generation_mode,
            generation_attempts=attempts,
            generation_error=generation_error,
        )
    except Exception as exc:
        payload.update(
            {
                "generationStatus": "failed",
                "generationError": "剧本生成失败",
                "generationAttempts": attempts,
            }
        )
        project.data = dict(payload)
        db.commit()
        raise HTTPException(status_code=500, detail="剧本生成失败") from exc


@router.get("/{project_id}/generation-status", response_model=GenerationStatusResponse)
def get_generation_status(project_id: str, db: Session = Depends(get_db)) -> GenerationStatusResponse:
    project = get_project_or_404(project_id, db)
    return GenerationStatusResponse(
        status=project.data.get("generationStatus", "pending"),
        mode=project.data.get("generationMode", ""),
        attempts=int(project.data.get("generationAttempts", 0)),
        error=project.data.get("generationError", ""),
        scene_count=len(project.data.get("scenes", [])),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectResponse:
    return project_response(get_project_or_404(project_id, db))


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, data: ProjectData, db: Session = Depends(get_db)) -> ProjectResponse:
    project = get_project_or_404(project_id, db)
    project.title = data.title
    project.data = data.model_dump(mode="json", by_alias=True)
    db.commit()
    db.refresh(project)
    return project_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> Response:
    project = get_project_or_404(project_id, db)
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
