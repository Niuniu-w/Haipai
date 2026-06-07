<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AlertCircle, ArrowLeft, ArrowRight, Check, CircleDashed, FileCheck2, LoaderCircle, RotateCw, Sparkles } from 'lucide-vue-next'
import {
  generateProjectChapter,
  getProjectGenerationStatus,
  startProjectGeneration,
  type GenerationStatusResponse,
  type ScriptGenerationResponse,
} from '../api/projects'
import type { GenerationChapterState, Project } from '../types'

const props = defineProps<{
  project: Project
  projectId: string
  backendConnected: boolean
  aiConfigured: boolean
  aiModel: string
}>()
const emit = defineEmits<{ back: []; next: []; notify: [message: string] }>()

const isGenerating = ref(false)
const activeChapterId = ref('')

const complete = computed(() => props.project.generationStatus === 'completed' && props.project.scenes.length > 0)
const completedCount = computed(() => props.project.generationChapters.filter((item) => item.status === 'completed').length)
const percentage = computed(() => props.project.chapters.length
  ? Math.round((completedCount.value / props.project.chapters.length) * 100)
  : 0)
const hasFailed = computed(() => props.project.generationChapters.some((item) => item.status === 'failed'))
const hasPending = computed(() => props.project.generationChapters.some((item) => item.status === 'pending'))
const initialized = computed(() => props.project.generationAttempts > 0 && props.project.generationChapters.length > 0)
const stages = ['初始化逐章任务', '逐章调用模型', '每章完成立即持久化', '全部章节生成完成']
const isRealModelMode = (mode: string) =>
  Boolean(mode) && !['demo', 'legacy-local', 'local-rules', 'local-rules-fallback', 'mixed'].includes(mode)
const stage = computed(() => {
  if (complete.value) return stages.length
  if (isGenerating.value || completedCount.value > 0 || hasFailed.value) return 1
  return initialized.value ? 1 : 0
})
const modeLabel = computed(() => {
  if (isRealModelMode(props.project.generationMode)) return '真实大模型生成'
  if (props.project.generationMode === 'local-rules-fallback') return '模型失败 · 本地回退'
  if (props.project.generationMode === 'local-rules') return '本地规则生成'
  return props.aiConfigured ? `将使用 ${props.aiModel}` : '将使用本地规则'
})

function chapterState(chapterId: string): GenerationChapterState {
  return props.project.generationChapters.find((item) => item.chapter_id === chapterId) ?? {
    chapter_id: chapterId,
    status: 'pending',
    mode: '',
    attempts: 0,
    error: '',
    scene_count: 0,
  }
}

function applyStatus(result: GenerationStatusResponse) {
  props.project.generationStatus = result.status
  props.project.generationMode = result.mode
  props.project.generationAttempts = result.attempts
  props.project.generationError = result.error
  props.project.generationChapters = result.chapter_statuses
}

function applyResult(result: ScriptGenerationResponse) {
  props.project.scenes = result.scenes
  props.project.generationStatus = result.generation_status
  props.project.generationMode = result.generation_mode
  props.project.generationAttempts = result.generation_attempts
  props.project.generationError = result.generation_error
  props.project.generationChapters = result.chapter_statuses
}

async function refreshStatus() {
  if (!props.projectId) return
  applyStatus(await getProjectGenerationStatus(props.projectId))
}

async function generateOneChapter(chapterId: string) {
  activeChapterId.value = chapterId
  const state = props.project.generationChapters.find((item) => item.chapter_id === chapterId)
  if (state) {
    state.status = 'running'
    state.error = ''
  }
  props.project.generationStatus = 'running'
  try {
    applyResult(await generateProjectChapter(props.projectId, chapterId))
    return true
  } catch {
    await refreshStatus()
    emit('notify', `${props.project.chapters.find((item) => item.id === chapterId)?.title ?? '章节'}生成失败，可单独重试`)
    return false
  } finally {
    activeChapterId.value = ''
  }
}

async function runPendingChapters() {
  for (const chapter of props.project.chapters) {
    if (chapterState(chapter.id).status !== 'pending') continue
    if (!await generateOneChapter(chapter.id)) break
  }
}

async function startGeneration() {
  if (isGenerating.value) return
  if (!props.backendConnected || !props.projectId) {
    props.project.generationStatus = 'failed'
    props.project.generationError = '请先连接后端再生成剧本'
    emit('notify', props.project.generationError)
    return
  }

  isGenerating.value = true
  try {
    applyStatus(await startProjectGeneration(props.projectId))
    await runPendingChapters()
    if (complete.value) emit('notify', `剧本生成完成，共 ${props.project.scenes.length} 个场景`)
  } catch {
    props.project.generationStatus = 'failed'
    props.project.generationError = '无法初始化逐章生成任务，请检查后端连接后重试'
    emit('notify', props.project.generationError)
  } finally {
    isGenerating.value = false
  }
}

async function continueGeneration() {
  if (isGenerating.value) return
  isGenerating.value = true
  try {
    await runPendingChapters()
    if (complete.value) emit('notify', `剧本生成完成，共 ${props.project.scenes.length} 个场景`)
  } finally {
    isGenerating.value = false
  }
}

async function retryChapter(chapterId: string) {
  if (isGenerating.value) return
  isGenerating.value = true
  try {
    if (await generateOneChapter(chapterId)) emit('notify', '该章节已重新生成并保存')
  } finally {
    isGenerating.value = false
  }
}

onMounted(async () => {
  if (!props.backendConnected || !props.projectId) {
    if (!complete.value) {
      props.project.generationStatus = 'failed'
      props.project.generationError = '请先连接后端再生成剧本'
    }
    return
  }
  try {
    await refreshStatus()
    if (complete.value) return
    if (!props.project.generationAttempts) await startGeneration()
    else if (!hasFailed.value) await continueGeneration()
  } catch {
    props.project.generationStatus = 'failed'
    props.project.generationError = '无法读取后端生成状态'
  }
})
</script>

<template>
  <section class="generate-page">
    <div class="generate-glow"></div>
    <div class="generate-card">
      <div class="generate-mark"><Sparkles :size="24" /></div>
      <span class="section-index">03 / GENERATE</span>
      <h2>{{ complete ? '剧本初稿已准备好' : project.generationStatus === 'failed' ? '剧本生成未完成' : '正在逐章把文字变成镜头' }}</h2>
      <p>{{ complete ? `${modeLabel}，所有章节均已保存到后端。` : project.generationStatus === 'failed' ? project.generationError : `${modeLabel}，每完成一章就会立即保存。` }}</p>

      <div class="progress-orbit" :style="{ '--progress': percentage + '%' }">
        <div><strong>{{ percentage }}<small>%</small></strong><span>{{ complete ? '生成完成' : '真实进度' }}</span></div>
      </div>

      <div class="generation-detail">
        <div class="stage-list">
          <div v-for="(item, index) in stages" :key="item" :class="{ active: stage === index && isGenerating, done: stage > index || complete }">
            <span><Check v-if="stage > index || complete" :size="13" /><LoaderCircle v-else-if="stage === index && isGenerating" :size="14" /><CircleDashed v-else :size="14" /></span>
            {{ item }}
          </div>
        </div>
        <div class="chapter-progress">
          <div class="chapter-progress-head"><span>章节生成状态</span><b>{{ completedCount }} / {{ project.chapters.length }}</b></div>
          <div v-for="(chapter, index) in project.chapters" :key="chapter.id" class="generation-row">
            <span class="generation-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <b>{{ chapter.title }}</b>
            <div v-if="chapterState(chapter.id).status === 'completed'" class="chapter-complete-actions">
              <span class="status done"><FileCheck2 :size="14" /> 已完成 · {{ chapterState(chapter.id).scene_count }} 场</span>
              <button title="只重新生成本章" :disabled="isGenerating" @click="retryChapter(chapter.id)"><RotateCw :size="12" /></button>
            </div>
            <span v-else-if="chapterState(chapter.id).status === 'running' || activeChapterId === chapter.id" class="status running"><LoaderCircle :size="14" /> 生成中</span>
            <button v-else-if="chapterState(chapter.id).status === 'failed'" class="chapter-retry" :disabled="isGenerating" @click="retryChapter(chapter.id)">
              <AlertCircle :size="13" /> 失败 · 重试
            </button>
            <span v-else class="status waiting">等待中</span>
          </div>
        </div>
      </div>

      <div class="generate-actions">
        <button class="button ghost" @click="$emit('back')"><ArrowLeft :size="16" /> 返回设置</button>
        <button v-if="!complete && hasPending && initialized" class="button soft" :disabled="isGenerating || hasFailed" @click="continueGeneration">
          <LoaderCircle v-if="isGenerating" :size="15" /><RotateCw v-else :size="15" /> 继续生成剩余章节
        </button>
        <button v-if="!complete" class="button soft" :disabled="isGenerating" @click="startGeneration"><RotateCw :size="15" /> 重新生成全部</button>
        <button class="button primary" :disabled="!complete" @click="$emit('next')">进入剧本工作台 <ArrowRight :size="16" /></button>
      </div>
    </div>
  </section>
</template>
