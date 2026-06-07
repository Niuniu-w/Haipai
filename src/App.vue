<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Check, Cloud, Feather, LayoutDashboard, Sparkles } from 'lucide-vue-next'
import { checkBackendHealth, type BackendStatus } from './api/health'
import {
  createProject,
  deleteProject,
  getProject,
  listProjects,
  updateProject,
  ApiRequestError,
  type ProjectSummary,
} from './api/projects'
import HomeView from './components/HomeView.vue'
import ImportView from './components/ImportView.vue'
import AnalysisView from './components/AnalysisView.vue'
import GenerateView from './components/GenerateView.vue'
import WorkspaceView from './components/WorkspaceView.vue'
import { defaultProject, sampleNovel } from './data'
import type { Project, ViewName } from './types'
import { normalizeProjectScenes, parseChapters } from './utils'

const LOCAL_PROJECT_KEY = 'storyforge-project'
const LOCAL_UPDATED_KEY = 'storyforge-project-local-updated-at'
const stored = localStorage.getItem(LOCAL_PROJECT_KEY)
let initialProject = structuredClone(defaultProject)
if (stored) {
  try {
    initialProject = JSON.parse(stored) as Project
  } catch {
    localStorage.removeItem(LOCAL_PROJECT_KEY)
  }
}
const project = reactive<Project>(initialProject)
normalizeProjectScenes(project)
if (!project.chapters.length) project.chapters = parseChapters(project.rawText)
if (!Number.isFinite(Date.parse(project.updatedAt))) {
  const storedUpdatedAt = localStorage.getItem(LOCAL_UPDATED_KEY)
  project.updatedAt = storedUpdatedAt && Number.isFinite(Date.parse(storedUpdatedAt))
    ? storedUpdatedAt
    : new Date(0).toISOString()
}
project.analysisStatus ??= 'pending'
project.analysisMode ??= ''
project.analysisError ??= ''
project.analysisAttempts ??= 0
project.generationStatus ??= project.scenes.length ? 'completed' : 'pending'
project.generationMode ??= project.scenes.length ? 'legacy-local' : ''
project.generationError ??= ''
project.generationAttempts ??= 0
project.generationChapters ??= []
project.revision ??= 0
project.dialogueDensity ??= '密集'
project.targetSceneCount ??= Math.max(project.chapters.length, 1)
const remoteProjectId = ref(localStorage.getItem('storyforge-project-id') ?? '')
const storedRevision = localStorage.getItem('storyforge-project-revision') ?? ''
const remoteRevision = ref(/^\d+$/.test(storedRevision) ? storedRevision : '')
const projectHistory = ref<ProjectSummary[]>([])

const view = ref<ViewName>('home')
const saved = ref(true)
const remoteSaved = ref(false)
const toast = ref('')
const backendStatus = ref<BackendStatus>('checking')
let toastTimer: number | undefined
let saveTimer: number | undefined
let remoteSaveTimer: number | undefined
let healthTimer: number | undefined
let applyingProject = false
let touchingUpdatedAt = false
let changeVersion = 0
let projectContextVersion = 0
let backendSaveQueue: Promise<void> = Promise.resolve()
let lastConflictVersion = -1

const steps: { id: ViewName; label: string }[] = [
  { id: 'import', label: '导入原著' },
  { id: 'analysis', label: '故事分析' },
  { id: 'generate', label: '剧本生成' },
  { id: 'workspace', label: '编辑导出' },
]

const currentStep = computed(() => steps.findIndex((step) => step.id === view.value))
const saveLabel = computed(() => {
  if (!saved.value) return '保存中…'
  return '已保存'
})

watch(
  project,
  () => {
    if (applyingProject) return
    changeVersion += 1
    if (!touchingUpdatedAt) {
      touchingUpdatedAt = true
      project.updatedAt = new Date().toISOString()
      queueMicrotask(() => (touchingUpdatedAt = false))
    }
    saved.value = false
    remoteSaved.value = false
    window.clearTimeout(saveTimer)
    window.clearTimeout(remoteSaveTimer)
    saveTimer = window.setTimeout(() => {
      localStorage.setItem(LOCAL_PROJECT_KEY, JSON.stringify(project))
      localStorage.setItem(LOCAL_UPDATED_KEY, project.updatedAt)
      saved.value = true
    }, 450)
    remoteSaveTimer = window.setTimeout(() => saveProjectToBackend(), 900)
  },
  { deep: true },
)

function notify(message: string) {
  toast.value = message
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = ''), 2400)
}

async function refreshBackendStatus(syncProject = true) {
  backendStatus.value = 'checking'
  backendStatus.value = (await checkBackendHealth()) ? 'connected' : 'disconnected'
  if (backendStatus.value === 'connected' && syncProject && !remoteSaved.value) {
    await saveProjectToBackend()
    await refreshProjectHistory()
  }
}

async function refreshProjectHistory() {
  if (backendStatus.value !== 'connected') return
  try {
    projectHistory.value = await listProjects()
  } catch {
    projectHistory.value = []
  }
}

async function saveProjectToBackend(showResult = false) {
  if (
    backendStatus.value !== 'connected'
    || project.analysisStatus === 'running'
    || project.generationStatus === 'running'
  ) return Promise.resolve(false)

  const snapshot = JSON.parse(JSON.stringify(project)) as Project
  const requestedVersion = changeVersion
  const requestedContext = projectContextVersion
  const operation = backendSaveQueue.then(async () => {
    if (backendStatus.value !== 'connected' || requestedContext !== projectContextVersion) return false
    const targetProjectId = remoteProjectId.value
    const targetRevision = remoteRevision.value
    try {
      const response = targetProjectId
        ? await updateProject(targetProjectId, snapshot, targetRevision)
        : await createProject(snapshot)
      if (requestedContext !== projectContextVersion) return false
      remoteProjectId.value = response.id
      remoteRevision.value = String(response.data.revision)
      localStorage.setItem('storyforge-project-id', response.id)
      localStorage.setItem('storyforge-project-revision', remoteRevision.value)
      remoteSaved.value = requestedVersion === changeVersion
      await refreshProjectHistory()
      if (showResult) notify('项目已保存')
      return true
    } catch (error) {
      remoteSaved.value = false
      if (error instanceof ApiRequestError && [409, 428].includes(error.status)) {
        if (lastConflictVersion !== changeVersion) {
          lastConflictVersion = changeVersion
          notify('项目已有其他更新，当前修改已保留；请重新打开项目后再合并修改')
        }
      } else if (showResult) {
        notify('保存失败，请稍后重试')
      }
      return false
    }
  })
  backendSaveQueue = operation.then(() => undefined, () => undefined)
  return operation
}

async function saveNow() {
  project.updatedAt = new Date().toISOString()
  await nextTick()
  window.clearTimeout(saveTimer)
  window.clearTimeout(remoteSaveTimer)
  localStorage.setItem(LOCAL_PROJECT_KEY, JSON.stringify(project))
  localStorage.setItem(LOCAL_UPDATED_KEY, project.updatedAt)
  saved.value = true
  if (backendStatus.value === 'connected') {
    return saveProjectToBackend(true)
  } else {
    notify('项目已保存')
    return true
  }
}

async function openAnalysis() {
  if (backendStatus.value === 'connected' && !await saveProjectToBackend()) return
  view.value = 'analysis'
}

async function beginGeneration() {
  if (backendStatus.value === 'connected' && !await saveProjectToBackend()) return
  view.value = 'generate'
}

async function loadRemoteProject() {
  if (backendStatus.value !== 'connected' || !remoteProjectId.value) return
  try {
    const response = await getProject(remoteProjectId.value)
    const localUpdatedAt = Date.parse(localStorage.getItem(LOCAL_UPDATED_KEY) ?? project.updatedAt)
    const remoteUpdatedAt = Math.max(
      Number.isFinite(Date.parse(response.data.updatedAt)) ? Date.parse(response.data.updatedAt) : 0,
      Date.parse(response.updated_at),
    )
    if (stored && Number.isFinite(localUpdatedAt) && localUpdatedAt > remoteUpdatedAt) {
      remoteRevision.value = String(response.data.revision)
      localStorage.setItem('storyforge-project-revision', remoteRevision.value)
      if (await saveProjectToBackend()) notify('项目已保存')
    } else {
      await applyRemoteProject(response.data, response.updated_at)
    }
  } catch {
    resetRemoteProject()
  }
}

async function openRemoteProject(projectId: string) {
  try {
    await backendSaveQueue
    const response = await getProject(projectId)
    projectContextVersion += 1
    remoteProjectId.value = response.id
    localStorage.setItem('storyforge-project-id', response.id)
    await applyRemoteProject(response.data, response.updated_at)
    view.value = project.scenes.length ? 'workspace' : 'import'
    notify(`已打开《${project.title}》`)
  } catch {
    notify('项目加载失败，请稍后重试')
  }
}

async function removeRemoteProject(projectId: string) {
  const item = projectHistory.value.find((projectItem) => projectItem.id === projectId)
  if (!window.confirm(`确认删除项目《${item?.title ?? '未命名项目'}》？此操作无法撤销。`)) return
  try {
    await backendSaveQueue
    await deleteProject(projectId)
    if (remoteProjectId.value === projectId) resetRemoteProject()
    await refreshProjectHistory()
    notify('项目已删除')
  } catch {
    notify('项目删除失败，请稍后重试')
  }
}

function resetRemoteProject() {
  projectContextVersion += 1
  remoteProjectId.value = ''
  remoteRevision.value = ''
  remoteSaved.value = false
  localStorage.removeItem('storyforge-project-id')
  localStorage.removeItem('storyforge-project-revision')
}

async function applyRemoteProject(data: Project, updatedAt: string) {
  applyingProject = true
  Object.assign(project, data)
  normalizeProjectScenes(project)
  project.updatedAt = updatedAt
  remoteRevision.value = String(data.revision)
  await nextTick()
  applyingProject = false
  localStorage.setItem('storyforge-project-revision', remoteRevision.value)
  localStorage.setItem(LOCAL_PROJECT_KEY, JSON.stringify(project))
  localStorage.setItem(LOCAL_UPDATED_KEY, project.updatedAt)
  saved.value = true
  remoteSaved.value = true
}

async function startDemo() {
  resetRemoteProject()
  Object.assign(project, structuredClone(defaultProject))
  project.updatedAt = new Date().toISOString()
  project.rawText = sampleNovel
  project.chapters = parseChapters(sampleNovel)
  view.value = 'import'
  await saveProjectToBackend()
  notify('已载入内置示例小说')
}

async function newProject() {
  resetRemoteProject()
  Object.assign(project, {
    ...structuredClone(defaultProject),
    title: '未命名故事',
    filename: '',
    rawText: '',
    genre: '',
    style: '',
    era: '',
    summary: '',
    adaptationMode: '忠于原著',
    scriptType: '电影',
    dialogueDensity: '密集',
    targetSceneCount: 3,
    chapters: [],
    characters: [],
    relationships: [],
    scenes: [],
    analysisStatus: 'pending',
    analysisMode: '',
    analysisError: '',
    analysisAttempts: 0,
    generationStatus: 'pending',
    generationMode: '',
    generationError: '',
    generationAttempts: 0,
    generationChapters: [],
    updatedAt: new Date().toISOString(),
    revision: 0,
  })
  view.value = 'import'
  await saveProjectToBackend()
}

onMounted(() => {
  document.title = '织幕 · AI 小说剧本工坊'
  refreshBackendStatus(false).then(async () => {
    await loadRemoteProject()
    await refreshProjectHistory()
  })
  healthTimer = window.setInterval(() => refreshBackendStatus(), 30000)
})

onBeforeUnmount(() => {
  window.clearInterval(healthTimer)
  window.clearTimeout(saveTimer)
  window.clearTimeout(remoteSaveTimer)
})
</script>

<template>
  <div class="app-shell" :class="{ 'workspace-mode': view === 'workspace' }">
    <header class="topbar">
      <button class="brand" @click="view = 'home'">
        <span class="brand-mark"><Feather :size="18" /></span>
        <span class="brand-name">织幕</span>
        <span class="brand-sub">STORYFORGE</span>
      </button>

      <nav v-if="view !== 'home'" class="step-nav">
        <button
          v-for="(step, index) in steps"
          :key="step.id"
          class="step-item"
          :class="{ active: view === step.id, done: currentStep > index }"
          @click="currentStep >= index ? (view = step.id) : undefined"
        >
          <span class="step-dot"><Check v-if="currentStep > index" :size="11" />{{ currentStep <= index ? index + 1 : '' }}</span>
          {{ step.label }}
        </button>
      </nav>

      <div class="top-actions">
        <span v-if="view !== 'home'" class="save-state">
          <Cloud :size="14" />
          {{ saveLabel }}
        </span>
        <button v-if="view !== 'home'" class="icon-button" title="返回首页" @click="view = 'home'">
          <LayoutDashboard :size="17" />
        </button>
        <div class="avatar">WN</div>
      </div>
    </header>

    <main>
      <HomeView
        v-if="view === 'home'"
        :project="project"
        :projects="projectHistory"
        @start="newProject"
        @demo="startDemo"
        @continue="view = 'workspace'"
        @open="openRemoteProject"
        @remove="removeRemoteProject"
      />
      <ImportView
        v-else-if="view === 'import'"
        :project="project"
        :project-id="remoteProjectId"
        :backend-connected="backendStatus === 'connected'"
        @next="openAnalysis"
        @notify="notify"
      />
      <AnalysisView
        v-else-if="view === 'analysis'"
        :project="project"
        :project-id="remoteProjectId"
        :backend-connected="backendStatus === 'connected'"
        @back="view = 'import'"
        @next="beginGeneration"
        @notify="notify"
      />
      <GenerateView
        v-else-if="view === 'generate'"
        :project="project"
        :project-id="remoteProjectId"
        :backend-connected="backendStatus === 'connected'"
        @back="view = 'analysis'"
        @next="view = 'workspace'"
        @notify="notify"
      />
      <WorkspaceView
        v-else
        :project="project"
        :project-id="remoteProjectId"
        :backend-connected="backendStatus === 'connected'"
        :save-project="saveNow"
        @back="view = 'generate'"
        @notify="notify"
        @save="saveNow"
      />
    </main>

    <Transition name="toast">
      <div v-if="toast" class="toast"><Sparkles :size="16" />{{ toast }}</div>
    </Transition>
  </div>
</template>
