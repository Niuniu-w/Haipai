<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowLeft, ArrowRight, Check, CircleDashed, FileCheck2, LoaderCircle, RotateCw, Sparkles } from 'lucide-vue-next'
import type { Project } from '../types'
import { buildScenes } from '../utils'

const props = defineProps<{ project: Project }>()
defineEmits<{ back: []; next: [] }>()

const completeCount = ref(0)
const stage = ref(0)
let timer: number | undefined

const percentage = computed(() => Math.round((completeCount.value / props.project.chapters.length) * 100) || 0)
const complete = computed(() => completeCount.value >= props.project.chapters.length)
const stages = ['整理全局故事上下文', '逐章生成场景与对白', '校验人物与事件一致性', '组装结构化剧本']

onMounted(() => {
  if (!props.project.scenes.length) props.project.scenes = buildScenes(props.project.chapters)
  timer = window.setInterval(() => {
    if (completeCount.value < props.project.chapters.length) {
      completeCount.value += 1
      stage.value = Math.min(3, Math.floor((completeCount.value / props.project.chapters.length) * 4))
    } else {
      window.clearInterval(timer)
    }
  }, 650)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <section class="generate-page">
    <div class="generate-glow"></div>
    <div class="generate-card">
      <div class="generate-mark"><Sparkles :size="24" /></div>
      <span class="section-index">03 / GENERATE</span>
      <h2>{{ complete ? '剧本初稿已准备好' : '正在把文字变成镜头' }}</h2>
      <p>{{ complete ? '所有章节都已通过结构校验，可以进入工作台继续打磨。' : `AI 正在理解《${project.title}》的每一个章节，请稍候。` }}</p>

      <div class="progress-orbit" :style="{ '--progress': percentage + '%' }">
        <div><strong>{{ percentage }}<small>%</small></strong><span>{{ complete ? '生成完成' : '总体进度' }}</span></div>
      </div>

      <div class="generation-detail">
        <div class="stage-list">
          <div v-for="(item, index) in stages" :key="item" :class="{ active: stage === index && !complete, done: stage > index || complete }">
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
            <span v-else-if="index === completeCount" class="status running"><LoaderCircle :size="14" /> 生成中</span>
            <span v-else class="status waiting">等待中</span>
          </div>
        </div>
      </div>

      <div class="generate-actions">
        <button class="button ghost" @click="$emit('back')"><ArrowLeft :size="16" /> 返回设置</button>
        <button v-if="!complete" class="button soft" @click="completeCount = 0"><RotateCw :size="15" /> 重新开始</button>
        <button class="button primary" :disabled="!complete" @click="$emit('next')">进入剧本工作台 <ArrowRight :size="16" /></button>
      </div>
    </div>
  </section>
</template>
