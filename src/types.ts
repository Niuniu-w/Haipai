export type ViewName = 'home' | 'import' | 'analysis' | 'generate' | 'workspace'

export interface Chapter {
  id: string
  title: string
  content: string
  summary: string
  keyEvents: string[]
}

export interface Character {
  id: string
  name: string
  role: string
  description: string
  color: string
}

export interface Relationship {
  from: string
  to: string
  relation: string
}

export interface Dialogue {
  id: string
  character: string
  emotion: string
  line: string
}

export interface Scene {
  id: string
  chapterId: string
  sourceChapter: string
  title: string
  location: string
  time: string
  atmosphere: string
  characters: string[]
  actions: string[]
  dialogues: Dialogue[]
  sourceSummary: string
}

export interface GenerationChapterState {
  chapter_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  mode: string
  attempts: number
  error: string
  scene_count: number
}

export interface Project {
  title: string
  filename: string
  rawText: string
  genre: string
  style: string
  era: string
  summary: string
  adaptationMode: string
  scriptType: string
  chapters: Chapter[]
  characters: Character[]
  relationships: Relationship[]
  scenes: Scene[]
  updatedAt: string
  analysisStatus: 'pending' | 'running' | 'completed' | 'failed'
  analysisMode: string
  analysisError: string
  analysisAttempts: number
  generationStatus: 'pending' | 'running' | 'completed' | 'failed'
  generationMode: string
  generationError: string
  generationAttempts: number
  generationChapters: GenerationChapterState[]
}
