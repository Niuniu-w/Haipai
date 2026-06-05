<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Check, Cloud, Feather, LayoutDashboard, Sparkles } from 'lucide-vue-next'
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

const view = ref<ViewName>('home')
const saved = ref(true)
const toast = ref('')
let toastTimer: number | undefined
let saveTimer: number | undefined

const steps: { id: ViewName; label: string }[] = [
  { id: 'import', label: '导入原著' },
  { id: 'analysis', label: '故事分析' },
  { id: 'generate', label: '剧本生成' },
  { id: 'workspace', label: '编辑导出' },
]

const currentStep = computed(() => steps.findIndex((step) => step.id === view.value))

watch(
  project,
  () => {
    saved.value = false
    window.clearTimeout(saveTimer)
    saveTimer = window.setTimeout(() => {
      localStorage.setItem('storyforge-project', JSON.stringify(project))
      saved.value = true
    }, 450)
  },
  { deep: true },
)

function notify(message: string) {
  toast.value = message
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = ''), 2400)
}

function startDemo() {
  Object.assign(project, structuredClone(defaultProject))
  project.rawText = sampleNovel
  project.chapters = parseChapters(sampleNovel)
  view.value = 'import'
  notify('已载入内置示例小说')
}

function newProject() {
  Object.assign(project, {
    ...structuredClone(defaultProject),
    title: '未命名故事',
    filename: '',
    rawText: '',
    chapters: [],
    scenes: [],
  })
  view.value = 'import'
}

onMounted(() => {
  document.title = '织幕 · AI 小说剧本工坊'
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
          {{ saved ? '已自动保存' : '保存中…' }}
        </span>
        <button v-if="view !== 'home'" class="icon-button" title="返回首页" @click="view = 'home'">
          <LayoutDashboard :size="17" />
        </button>
        <div class="avatar">WN</div>
      </div>
    </header>

    <main>
      <HomeView v-if="view === 'home'" :project="project" @start="newProject" @demo="startDemo" @continue="view = 'workspace'" />
      <ImportView v-else-if="view === 'import'" :project="project" @next="view = 'analysis'" @notify="notify" />
      <AnalysisView v-else-if="view === 'analysis'" :project="project" @back="view = 'import'" @next="view = 'generate'" @notify="notify" />
      <GenerateView v-else-if="view === 'generate'" :project="project" @back="view = 'analysis'" @next="view = 'workspace'" />
      <WorkspaceView v-else :project="project" @back="view = 'generate'" @notify="notify" />
    </main>

    <Transition name="toast">
      <div v-if="toast" class="toast"><Sparkles :size="16" />{{ toast }}</div>
    </Transition>
  </div>
</template>
