<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowLeft, ArrowRight, Check, CircleDashed, FileCheck2, LoaderCircle, RotateCw, Sparkles } from 'lucide-vue-next'
import { generateProjectScript } from '../api/projects'
import type { Project } from '../types'

const props = defineProps<{
  project: Project
  projectId: string
  backendConnected: boolean
  aiConfigured: boolean
  aiModel: string
}>()
const emit = defineEmits<{ back: []; next: []; notify: [message: string] }>()

const completeCount = ref(0)
const stage = ref(0)
const percentage = ref(0)
const isGenerating = ref(false)
let timer: number | undefined

const complete = computed(() => props.project.generationStatus === 'completed' && props.project.scenes.length > 0)
const stages = ['整理全局故事上下文', '逐章生成场景与对白', '校验人物与事件一致性', '组装结构化剧本']
const modeLabel = computed(() => {
  if (props.project.generationMode.startsWith('openai-responses:')) return '真实大模型生成'
  if (props.project.generationMode === 'local-rules-fallback') return '模型失败 · 本地回退'
  if (props.project.generationMode === 'local-rules') return '本地规则生成'
  return props.aiConfigured ? `将使用 ${props.aiModel}` : '将使用本地规则'
})

function startProgress() {
  window.clearInterval(timer)
  percentage.value = 6
  completeCount.value = 0
  stage.value = 0
  timer = window.setInterval(() => {
    percentage.value = Math.min(88, percentage.value + 4)
    stage.value = Math.min(3, Math.floor(percentage.value / 25))
    completeCount.value = Math.min(
      Math.max(0, props.project.chapters.length - 1),
      Math.floor((percentage.value / 100) * props.project.chapters.length),
    )
  }, 450)
}

async function runGeneration() {
  if (isGenerating.value) return
  if (!props.backendConnected || !props.projectId) {
    props.project.generationStatus = 'failed'
    props.project.generationError = '请先连接后端再生成剧本'
    emit('notify', props.project.generationError)
    return
  }

  isGenerating.value = true
  props.project.generationStatus = 'running'
  props.project.generationError = ''
  startProgress()
  try {
    const result = await generateProjectScript(props.projectId)
    props.project.scenes = result.scenes
    props.project.generationStatus = result.generation_status
    props.project.generationMode = result.generation_mode
    props.project.generationAttempts = result.generation_attempts
    props.project.generationError = result.generation_error
    completeCount.value = props.project.chapters.length
    stage.value = stages.length
    percentage.value = 100
    emit(
      'notify',
      result.generation_mode === 'local-rules-fallback'
        ? `大模型生成失败，已回退本地生成 ${result.scene_count} 个场景`
        : `剧本生成完成，共 ${result.scene_count} 个场景`,
    )
  } catch {
    props.project.generationStatus = 'failed'
    props.project.generationError = '剧本生成失败，请检查后端连接后重试'
    percentage.value = 0
    emit('notify', props.project.generationError)
  } finally {
    window.clearInterval(timer)
    isGenerating.value = false
  }
}

onMounted(() => {
  if (complete.value) {
    completeCount.value = props.project.chapters.length
    stage.value = stages.length
    percentage.value = 100
  } else {
    runGeneration()
  }
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <section class="generate-page">
    <div class="generate-glow"></div>
    <div class="generate-card">
      <div class="generate-mark"><Sparkles :size="24" /></div>
      <span class="section-index">03 / GENERATE</span>
      <h2>{{ complete ? '剧本初稿已准备好' : project.generationStatus === 'failed' ? '剧本生成未完成' : '正在把文字变成镜头' }}</h2>
      <p>{{ complete ? `${modeLabel}，所有场景已保存到后端。` : project.generationStatus === 'failed' ? project.generationError : `${modeLabel}，正在改编《${project.title}》。` }}</p>

      <div class="progress-orbit" :style="{ '--progress': percentage + '%' }">
        <div><strong>{{ percentage }}<small>%</small></strong><span>{{ complete ? '生成完成' : '总体进度' }}</span></div>
      </div>

      <div class="generation-detail">
        <div class="stage-list">
          <div v-for="(item, index) in stages" :key="item" :class="{ active: stage === index && isGenerating, done: stage > index || complete }">
            <span><Check v-if="stage > index || complete" :size="13" /><LoaderCircle v-else-if="stage === index" :size="14" /><CircleDashed v-else :size="14" /></span>
            {{ item }}
          </div>
        </div>
        <div class="chapter-progress">
          <div class="chapter-progress-head"><span>章节生成状态</span><b>{{ completeCount }} / {{ project.chapters.length }}</b></div>
          <div v-for="(chapter, index) in project.chapters" :key="chapter.id" class="generation-row">
            <span class="generation-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <b>{{ chapter.title }}</b>
            <span v-if="index < completeCount" class="status done"><FileCheck2 :size="14" /> 已完成</span>
            <span v-else-if="index === completeCount && isGenerating" class="status running"><LoaderCircle :size="14" /> 生成中</span>
            <span v-else class="status waiting">等待中</span>
          </div>
        </div>
      </div>

      <div class="generate-actions">
        <button class="button ghost" @click="$emit('back')"><ArrowLeft :size="16" /> 返回设置</button>
        <button v-if="!complete" class="button soft" :disabled="isGenerating" @click="runGeneration"><RotateCw :size="15" /> 重新生成</button>
        <button class="button primary" :disabled="!complete" @click="$emit('next')">进入剧本工作台 <ArrowRight :size="16" /></button>
      </div>
    </div>
  </section>
</template>
