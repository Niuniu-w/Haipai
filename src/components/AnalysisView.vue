<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowLeft, ArrowRight, BookMarked, Check, LoaderCircle, Network, Plus, Sparkles, Trash2, UserRound, X } from 'lucide-vue-next'
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
const dialogueDensities: Project['dialogueDensity'][] = ['少量', '均衡', '密集']
const hasAnalysis = computed(() => Boolean(props.project.summary || props.project.characters.length || props.project.relationships.length))
const canAnalyze = computed(() => props.backendConnected && Boolean(props.projectId) && props.project.chapters.length >= 3)
const characterColors = ['#bd6c55', '#6f8674', '#7c7894', '#b08968', '#617c8b', '#9a6d78']
const previousCharacterNames = new Map<string, string>()

function addCharacter() {
  const number = props.project.characters.length + 1
  props.project.characters.push({
    id: `character-${Date.now()}`,
    name: `新人物 ${number}`,
    role: '待定角色',
    description: '补充人物简介',
    color: characterColors[(number - 1) % characterColors.length],
  })
  emit('notify', '已添加人物，可直接编辑人物信息')
}

function rememberCharacterName(characterId: string, name: string) {
  previousCharacterNames.set(characterId, name)
}

function syncCharacterName(characterId: string, name: string) {
  const previous = previousCharacterNames.get(characterId)
  previousCharacterNames.delete(characterId)
  if (!previous || previous === name) return
  props.project.relationships.forEach((relationship) => {
    if (relationship.from === previous) relationship.from = name
    if (relationship.to === previous) relationship.to = name
  })
  props.project.scenes.forEach((scene) => {
    scene.characters = scene.characters.map((character) => character === previous ? name : character)
    scene.dialogues.forEach((dialogue) => {
      if (dialogue.character === previous) dialogue.character = name
    })
  })
  emit('notify', `已同步更新“${previous}”的全部引用`)
}

function removeCharacter(characterId: string) {
  const character = props.project.characters.find((item) => item.id === characterId)
  if (!character || !window.confirm(`确认删除人物“${character.name}”？相关人物关系和对白也会删除。`)) return
  props.project.characters = props.project.characters.filter((item) => item.id !== characterId)
  props.project.relationships = props.project.relationships.filter(
    (relationship) => relationship.from !== character.name && relationship.to !== character.name,
  )
  props.project.scenes.forEach((scene) => {
    scene.characters = scene.characters.filter((name) => name !== character.name)
    scene.dialogues = scene.dialogues.filter((dialogue) => dialogue.character !== character.name)
  })
  emit('notify', `已删除人物“${character.name}”及其引用`)
}

function addRelationship() {
  if (props.project.characters.length < 2) {
    emit('notify', '至少需要两个人物才能添加关系')
    return
  }
  props.project.relationships.push({
    from: props.project.characters[0].name,
    to: props.project.characters[1].name,
    relation: '待补充关系',
  })
}

function addKeyEvent() {
  props.project.chapters[activeChapter.value]?.keyEvents.push('补充关键事件')
}

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
            <button class="text-button" @click="addCharacter"><Plus :size="14" /> 添加人物</button>
          </div>
          <div class="character-grid">
            <article v-for="character in project.characters" :key="character.id" class="character-card">
              <div class="character-avatar" :style="{ background: character.color }">{{ character.name.slice(0, 1) }}</div>
              <div class="character-fields">
                <input
                  v-model="character.name"
                  class="character-name"
                  aria-label="人物名称"
                  @focus="rememberCharacterName(character.id, character.name)"
                  @change="syncCharacterName(character.id, character.name)"
                />
                <input v-model="character.role" class="character-role" aria-label="人物角色" />
                <textarea v-model="character.description" rows="2" aria-label="人物简介"></textarea>
              </div>
              <button class="card-remove" :title="`删除 ${character.name}`" @click="removeCharacter(character.id)"><Trash2 :size="13" /></button>
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
            <div><span class="mini-label">章节概要</span><h3>{{ project.chapters[activeChapter].title }}</h3><textarea v-model="project.chapters[activeChapter].summary" rows="5"></textarea></div>
            <div class="events">
              <div class="event-head"><span class="mini-label">关键事件</span><button @click="addKeyEvent"><Plus :size="12" /> 添加</button></div>
              <ul>
                <li v-for="(_, eventIndex) in project.chapters[activeChapter].keyEvents" :key="eventIndex">
                  <Check :size="13" /><input v-model="project.chapters[activeChapter].keyEvents[eventIndex]" />
                  <button @click="project.chapters[activeChapter].keyEvents.splice(eventIndex, 1)"><X :size="11" /></button>
                </li>
              </ul>
            </div>
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
          <label class="setting-control"><span>对白密度</span><select v-model="project.dialogueDensity"><option v-for="density in dialogueDensities" :key="density" :value="density">{{ density }}</option></select></label>
          <label class="setting-control"><span>目标场景数</span><input v-model.number="project.targetSceneCount" type="number" :min="Math.max(project.chapters.length, 1)" :max="Math.max(project.chapters.length * 4, 4)" /></label>
          <p class="settings-note">目标场景会按章节分配，每章至少一场；真实模型与本地规则都会读取这两个参数。</p>
        </div>

        <div class="panel relation-card">
          <div class="panel-title">
            <div><Network :size="17" /><b>人物关系</b></div>
            <button class="text-button" @click="addRelationship"><Plus :size="13" /> 添加</button>
          </div>
          <div v-if="project.relationships.length" class="relation-editor">
            <div v-for="(item, index) in project.relationships" :key="index" class="relation-editor-row">
              <select v-model="item.from"><option v-for="character in project.characters" :key="character.id" :value="character.name">{{ character.name }}</option></select>
              <span>→</span>
              <select v-model="item.to"><option v-for="character in project.characters" :key="character.id" :value="character.name">{{ character.name }}</option></select>
              <input v-model="item.relation" placeholder="关系说明" />
              <button title="删除关系" @click="project.relationships.splice(index, 1)"><Trash2 :size="12" /></button>
            </div>
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
