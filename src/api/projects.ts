import type { Chapter, Project, Scene } from '../types'

interface ProjectResponse {
  id: string
  data: Project
  created_at: string
  updated_at: string
}

export interface ProjectSummary {
  id: string
  title: string
  chapter_count: number
  scene_count: number
  updated_at: string
}

export interface ChapterParseResponse {
  chapters: Chapter[]
  chapter_count: number
  valid: boolean
  minimum_required: number
}

export interface StoryAnalysisResponse {
  summary: string
  genre: string
  era: string
  style: string
  characters: Project['characters']
  relationships: Project['relationships']
  chapters: Chapter[]
  analysis_status: Project['analysisStatus']
  analysis_mode: string
  analysis_attempts: number
  analysis_error: string
}

export interface ScriptGenerationResponse {
  scenes: Scene[]
  scene_count: number
  generation_status: Project['generationStatus']
  generation_mode: string
  generation_attempts: number
  generation_error: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) throw new Error(`项目接口请求失败：${response.status}`)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function createProject(project: Project): Promise<ProjectResponse> {
  return request<ProjectResponse>('/api/projects', {
    method: 'POST',
    body: JSON.stringify(project),
  })
}

export async function listProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>('/api/projects')
}

export async function getProject(projectId: string): Promise<ProjectResponse> {
  return request<ProjectResponse>(`/api/projects/${projectId}`)
}

export async function updateProject(projectId: string, project: Project): Promise<ProjectResponse> {
  return request<ProjectResponse>(`/api/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(project),
  })
}

export async function deleteProject(projectId: string): Promise<void> {
  await request<void>(`/api/projects/${projectId}`, { method: 'DELETE' })
}

export async function parseProjectChapters(projectId: string, rawText: string): Promise<ChapterParseResponse> {
  return request<ChapterParseResponse>(`/api/projects/${projectId}/parse-chapters`, {
    method: 'POST',
    body: JSON.stringify({ raw_text: rawText }),
  })
}

export async function analyzeProject(projectId: string): Promise<StoryAnalysisResponse> {
  return request<StoryAnalysisResponse>(`/api/projects/${projectId}/analyze`, { method: 'POST' })
}

export async function generateProjectScript(projectId: string): Promise<ScriptGenerationResponse> {
  return request<ScriptGenerationResponse>(`/api/projects/${projectId}/generate`, { method: 'POST' })
}
