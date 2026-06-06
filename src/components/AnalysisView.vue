<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowLeft, ArrowRight, BookMarked, Check, ChevronDown, LoaderCircle, Network, Plus, Sparkles, UserRound } from 'lucide-vue-next'
import { analyzeProject } from '../api/projects'
import type { Project } from '../types'

const props = defineProps<{
  project: Project
  projectId: string
  backendConnected: boolean
  aiConfigured: boolean
  aiModel: string
}>()
const emit = defineEmits<{ back: []; next: []; notify: [message: string] }>()
const activeChapter = ref(0)
const isAnalyzing = ref(false)
const modes = ['忠于原著', '影视化增强', '短剧快节奏']
const scriptTypes = ['电影', '电视剧', '短剧']
const hasAnalysis = computed(() => Boolean(props.project.summary || props.project.characters.length || props.project.relationships.length))
const relationCore = computed(() => props.project.relationships[0]?.from ?? props.project.characters[0]?.name ?? '')
const canAnalyze = computed(() => props.backendConnected && Boolean(props.projectId) && props.project.chapters.length >= 3)

async function runAnalysis() {
  if (!canAnalyze.value || isAnalyzing.value) {
    emit('notify', props.backendConnected ? '至少需要 3 个章节才能开始分析' : '请先连接后端再开始分析')
    return
  }

  isAnalyzing.value = true
  props.project.analysisStatus = 'running'
  props.project.analysisError = ''
  try {
    const result = await analyzeProject(props.projectId)
    props.project.summary = result.summary
    props.project.genre = result.genre
    props.project.era = result.era
    props.project.style = result.style
    props.project.characters = result.characters
    props.project.relationships = result.relationships
    props.project.chapters = result.chapters
    props.project.analysisStatus = result.analysis_status
    props.project.analysisMode = result.analysis_mode
    props.project.analysisAttempts = result.analysis_attempts
    props.project.analysisError = result.analysis_error
    props.project.scenes = []
    props.project.generationStatus = 'pending'
    props.project.generationMode = ''
    props.project.generationError = ''
    props.project.generationAttempts = 0
    props.project.generationChapters = []
    emit(
      'notify',
      result.analysis_mode === 'local-rules-fallback'
        ? `大模型调用失败，已回退本地分析并识别 ${result.characters.length} 位主要人物`
        : `故事分析完成，识别 ${result.characters.length} 位主要人物`,
    )
  } catch {
    props.project.analysisStatus = 'failed'
    props.project.analysisError = '故事分析失败，请检查后端连接后重试'
    emit('notify', props.project.analysisError)
  } finally {
    isAnalyzing.value = false
  }
}
</script>

<template>
  <section class="flow-page analysis-page">
    <div class="flow-heading compact">
      <div>
        <span class="section-index">02 / ANALYSIS</span>
        <h2>故事骨架已经浮现</h2>
        <p>{{ aiConfigured ? `已配置 ${aiModel}，将优先使用真实大模型分析。` : '未配置大模型密钥，将使用可离线运行的本地规则分析。' }}</p>
      </div>
      <div class="analysis-score">
        <LoaderCircle v-if="isAnalyzing" class="spin" :size="18" />
        <Sparkles v-else :size="18" />
        <span v-if="isAnalyzing"><b>分析中</b> 正在理解人物与剧情</span>
        <span v-else-if="hasAnalysis"><b>已完成</b> {{ project.analysisMode.startsWith('openai-responses:') ? '真实大模型分析' : project.analysisMode === 'local-rules-fallback' ? '模型失败 · 本地回退' : '本地规则分析' }}</span>
        <span v-else><b>待分析</b> 当前展示基础文本解析结果</span>
      </div>
    </div>

    <div class="analysis-layout">
      <div class="analysis-main">
        <div class="panel summary-panel">
          <div class="panel-title">
            <div><BookMarked :size="17" /><b>全局故事概要</b></div>
            <button class="button soft small" :disabled="isAnalyzing || !canAnalyze" @click="runAnalysis">
              <LoaderCircle v-if="isAnalyzing" class="spin" :size="13" />
              <Sparkles v-else :size="13" />
              {{ isAnalyzing ? '分析中…' : hasAnalysis ? '重新分析' : aiConfigured ? '开始大模型分析' : '开始本地分析' }}
            </button>
          </div>
          <textarea v-model="project.summary"></textarea>
          <div class="meta-grid">
            <label>题材<input v-model="project.genre" /></label>
            <label>时代背景<input v-model="project.era" /></label>
            <label>整体风格<input v-model="project.style" /></label>
          </div>
        </div>

        <div class="panel">
          <div class="panel-title">
            <div><UserRound :size="17" /><b>主要人物</b><span class="count-pill">{{ project.characters.length }}</span></div>
            <button class="text-button"><Plus :size="14" /> 添加人物</button>
          </div>
          <div class="character-grid">
            <article v-for="character in project.characters" :key="character.id" class="character-card">
              <div class="character-avatar" :style="{ background: character.color }">{{ character.name.slice(0, 1) }}</div>
              <div><h4>{{ character.name }}</h4><span>{{ character.role }}</span><p>{{ character.description }}</p></div>
            </article>
          </div>
        </div>

        <div class="panel chapter-analysis">
          <div class="panel-title">
            <div><BookMarked :size="17" /><b>章节脉络</b></div>
            <span class="muted">{{ project.chapters.length }} 章已完成{{ hasAnalysis ? '分析' : '基础解析' }}</span>
          </div>
          <div class="chapter-tabs">
            <button v-for="(chapter, index) in project.chapters" :key="chapter.id" :class="{ active: index === activeChapter }" @click="activeChapter = index">{{ index + 1 }}</button>
          </div>
          <div v-if="project.chapters[activeChapter]" class="chapter-analysis-body">
            <div><span class="mini-label">章节概要</span><h3>{{ project.chapters[activeChapter].title }}</h3><p>{{ project.chapters[activeChapter].summary }}</p></div>
            <div class="events"><span class="mini-label">关键事件</span><ul><li v-for="event in project.chapters[activeChapter].keyEvents" :key="event"><Check :size="13" />{{ event }}</li></ul></div>
          </div>
        </div>
      </div>

      <aside class="analysis-side">
        <div class="panel settings-card">
          <div class="panel-title"><div><Sparkles :size="17" /><b>改编设置</b></div></div>
          <label class="control-label">改编模式</label>
          <div class="mode-list">
            <button v-for="mode in modes" :key="mode" :class="{ active: project.adaptationMode === mode }" @click="project.adaptationMode = mode">
              <span><b>{{ mode }}</b><small>{{ mode === '忠于原著' ? '保留原著节奏与细节' : mode === '影视化增强' ? '强化画面与戏剧冲突' : '更快节奏与密集反转' }}</small></span>
              <Check v-if="project.adaptationMode === mode" :size="15" />
            </button>
          </div>
          <label class="control-label">目标剧本类型</label>
          <div class="segmented">
            <button v-for="type in scriptTypes" :key="type" :class="{ active: project.scriptType === type }" @click="project.scriptType = type">{{ type }}</button>
          </div>
          <div class="setting-row"><span>对白密度</span><b>均衡</b><ChevronDown :size="14" /></div>
          <div class="setting-row"><span>目标场景数</span><b>{{ project.chapters.length }}–{{ project.chapters.length * 2 }} 场</b><ChevronDown :size="14" /></div>
        </div>

        <div class="panel relation-card">
          <div class="panel-title"><div><Network :size="17" /><b>人物关系</b></div></div>
          <div v-if="project.relationships.length" class="relation-map">
            <div class="relation-core">{{ relationCore }}</div>
            <div v-for="(item, index) in project.relationships.slice(0, 4)" :key="item.to" class="relation-node" :class="`node-${index + 1}`">
              <b>{{ item.to }}</b><small>{{ item.relation.split(' / ')[0] }}</small>
            </div>
            <svg viewBox="0 0 300 220"><line x1="150" y1="110" x2="50" y2="38" /><line x1="150" y1="110" x2="250" y2="38" /><line x1="150" y1="110" x2="50" y2="188" /><line x1="150" y1="110" x2="250" y2="188" /></svg>
          </div>
          <div v-else class="empty-state">
            <Network :size="28" />
            <b>尚未生成人物关系</b>
            <span>点击“开始分析”后将在这里展示</span>
          </div>
        </div>
      </aside>
    </div>

    <div class="flow-footer">
      <button class="button ghost" @click="$emit('back')"><ArrowLeft :size="16" /> 返回章节</button>
      <span>{{ project.analysisMode.startsWith('openai-responses:') ? '当前为真实大模型分析，所有结果均可编辑' : '当前为本地规则分析，所有结果均可编辑' }}</span>
      <button class="button primary" @click="$emit('next')">生成结构化剧本 <ArrowRight :size="16" /></button>
    </div>
  </section>
</template>
