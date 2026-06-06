<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Check, Cloud, Feather, LayoutDashboard, Server, Sparkles } from 'lucide-vue-next'
import { checkBackendHealth, getAIStatus, type AIStatus, type BackendStatus } from './api/health'
import {
  createProject,
  deleteProject,
  getProject,
  listProjects,
  updateProject,
  type ProjectSummary,
} from './api/projects'
import HomeView from './components/HomeView.vue'
import ImportView from './components/ImportView.vue'
import AnalysisView from './components/AnalysisView.vue'
import GenerateView from './components/GenerateView.vue'
import WorkspaceView from './components/WorkspaceView.vue'
import { defaultProject, sampleNovel } from './data'
import type { Project, ViewName } from './types'
import { parseChapters } from './utils'

const stored = localStorage.getItem('storyforge-project')
const project = reactive<Project>(stored ? JSON.parse(stored) : structuredClone(defaultProject))
if (!project.chapters.length) project.chapters = parseChapters(project.rawText)
project.analysisStatus ??= 'pending'
project.analysisMode ??= ''
project.analysisError ??= ''
project.analysisAttempts ??= 0
project.generationStatus ??= project.scenes.length ? 'completed' : 'pending'
project.generationMode ??= project.scenes.length ? 'legacy-local' : ''
project.generationError ??= ''
project.generationAttempts ??= 0
project.generationChapters ??= []
const remoteProjectId = ref(localStorage.getItem('storyforge-project-id') ?? '')
const projectHistory = ref<ProjectSummary[]>([])

const view = ref<ViewName>('home')
const saved = ref(true)
const remoteSaved = ref(false)
const toast = ref('')
const backendStatus = ref<BackendStatus>('checking')
const aiStatus = ref<AIStatus>({ configured: false, provider: 'openai-responses', model: '', fallback: 'local-rules' })
let toastTimer: number | undefined
let saveTimer: number | undefined
let remoteSaveTimer: number | undefined
let healthTimer: number | undefined

const steps: { id: ViewName; label: string }[] = [
  { id: 'import', label: '导入原著' },
  { id: 'analysis', label: '故事分析' },
  { id: 'generate', label: '剧本生成' },
  { id: 'workspace', label: '编辑导出' },
]

const currentStep = computed(() => steps.findIndex((step) => step.id === view.value))
const backendLabel = computed(() => {
  if (backendStatus.value === 'connected') return '后端已连接'
  if (backendStatus.value === 'disconnected') return '后端未连接'
  return '检查后端…'
})
const saveLabel = computed(() => {
  if (!saved.value) return '保存中…'
  if (backendStatus.value === 'connected' && remoteSaved.value) return '已同步后端'
  return '已保存本地'
})

watch(
  project,
  () => {
    saved.value = false
    remoteSaved.value = false
    window.clearTimeout(saveTimer)
    window.clearTimeout(remoteSaveTimer)
    saveTimer = window.setTimeout(() => {
      localStorage.setItem('storyforge-project', JSON.stringify(project))
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

async function refreshBackendStatus(showResult = false, syncProject = true) {
  backendStatus.value = 'checking'
  backendStatus.value = (await checkBackendHealth()) ? 'connected' : 'disconnected'
  if (backendStatus.value === 'connected') await refreshAIStatus()
  if (backendStatus.value === 'connected' && syncProject && !remoteSaved.value) {
    await saveProjectToBackend()
    await refreshProjectHistory()
  }
  if (showResult) notify(backendLabel.value)
}

async function refreshAIStatus() {
  try {
    aiStatus.value = await getAIStatus()
  } catch {
    aiStatus.value = { configured: false, provider: 'openai-responses', model: '', fallback: 'local-rules' }
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
  ) return

  try {
    const snapshot = JSON.parse(JSON.stringify(project)) as Project
    const response = remoteProjectId.value
      ? await updateProject(remoteProjectId.value, snapshot)
      : await createProject(snapshot)
    remoteProjectId.value = response.id
    localStorage.setItem('storyforge-project-id', response.id)
    remoteSaved.value = true
    saved.value = true
    await refreshProjectHistory()
    if (showResult) notify('项目已保存到后端')
  } catch {
    remoteSaved.value = false
    if (showResult) notify('后端保存失败，项目仍保存在浏览器')
  }
}

async function saveNow() {
  localStorage.setItem('storyforge-project', JSON.stringify(project))
  saved.value = true
  if (backendStatus.value === 'connected') {
    await saveProjectToBackend(true)
  } else {
    notify('后端未连接，项目已保存到浏览器')
  }
}

async function openAnalysis() {
  await saveProjectToBackend()
  view.value = 'analysis'
}

async function beginGeneration() {
  await saveProjectToBackend()
  view.value = 'generate'
}

async function loadRemoteProject() {
  if (backendStatus.value !== 'connected' || !remoteProjectId.value) return
  try {
    const response = await getProject(remoteProjectId.value)
    Object.assign(project, response.data)
    remoteSaved.value = true
  } catch {
    remoteProjectId.value = ''
    localStorage.removeItem('storyforge-project-id')
  }
}

async function openRemoteProject(projectId: string) {
  try {
    const response = await getProject(projectId)
    remoteProjectId.value = response.id
    localStorage.setItem('storyforge-project-id', response.id)
    Object.assign(project, response.data)
    remoteSaved.value = true
    view.value = project.scenes.length ? 'workspace' : 'import'
    notify(`已打开《${project.title}》`)
  } catch {
    notify('项目加载失败，请检查后端连接')
  }
}

async function removeRemoteProject(projectId: string) {
  try {
    await deleteProject(projectId)
    if (remoteProjectId.value === projectId) resetRemoteProject()
    await refreshProjectHistory()
    notify('项目已从后端删除')
  } catch {
    notify('项目删除失败，请稍后重试')
  }
}

function resetRemoteProject() {
  remoteProjectId.value = ''
  remoteSaved.value = false
  localStorage.removeItem('storyforge-project-id')
}

async function startDemo() {
  resetRemoteProject()
  Object.assign(project, structuredClone(defaultProject))
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
  })
  view.value = 'import'
  await saveProjectToBackend()
}

onMounted(() => {
  document.title = '织幕 · AI 小说剧本工坊'
  refreshBackendStatus(false, false).then(async () => {
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
        <button
          class="backend-state"
          :class="backendStatus"
          :title="backendStatus === 'disconnected' ? '点击重新检查后端连接' : backendLabel"
          @click="refreshBackendStatus(true)"
        >
          <Server :size="13" />
          {{ backendLabel }}
        </button>
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
        :ai-configured="aiStatus.configured"
        :ai-model="aiStatus.model"
        @back="view = 'import'"
        @next="beginGeneration"
        @notify="notify"
      />
      <GenerateView
        v-else-if="view === 'generate'"
        :project="project"
        :project-id="remoteProjectId"
        :backend-connected="backendStatus === 'connected'"
        :ai-configured="aiStatus.configured"
        :ai-model="aiStatus.model"
        @back="view = 'analysis'"
        @next="view = 'workspace'"
        @notify="notify"
      />
      <WorkspaceView
        v-else
        :project="project"
        :project-id="remoteProjectId"
        :backend-connected="backendStatus === 'connected'"
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
