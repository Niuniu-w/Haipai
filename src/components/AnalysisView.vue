<script setup lang="ts">
import { ref } from 'vue'
import { ArrowLeft, ArrowRight, BookMarked, Check, ChevronDown, Network, Plus, Sparkles, UserRound } from 'lucide-vue-next'
import type { Project } from '../types'

defineProps<{ project: Project }>()
defineEmits<{ back: []; next: []; notify: [message: string] }>()
const activeChapter = ref(0)
const modes = ['忠于原著', '影视化增强', '短剧快节奏']
const scriptTypes = ['电影', '电视剧', '短剧']
</script>

<template>
  <section class="flow-page analysis-page">
    <div class="flow-heading compact">
      <div>
        <span class="section-index">02 / ANALYSIS</span>
        <h2>故事骨架已经浮现</h2>
        <p>确认 AI 对人物和剧情的理解，它们会成为剧本生成的依据。</p>
      </div>
      <div class="analysis-score"><Sparkles :size="18" /><span><b>92%</b> 故事结构完整度</span></div>
    </div>

    <div class="analysis-layout">
      <div class="analysis-main">
        <div class="panel summary-panel">
          <div class="panel-title"><div><BookMarked :size="17" /><b>全局故事概要</b></div><span class="ai-label"><Sparkles :size="12" /> AI GENERATED</span></div>
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
          <div class="panel-title"><div><BookMarked :size="17" /><b>章节脉络</b></div><span class="muted">{{ project.chapters.length }} 章已完成分析</span></div>
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
          <div class="relation-map">
            <div class="relation-core">林墨</div>
            <div v-for="(item, index) in project.relationships.slice(0, 4)" :key="item.to" class="relation-node" :class="`node-${index + 1}`">
              <b>{{ item.to }}</b><small>{{ item.relation.split(' / ')[0] }}</small>
            </div>
            <svg viewBox="0 0 300 220"><line x1="150" y1="110" x2="50" y2="38" /><line x1="150" y1="110" x2="250" y2="38" /><line x1="150" y1="110" x2="50" y2="188" /><line x1="150" y1="110" x2="250" y2="188" /></svg>
          </div>
        </div>
      </aside>
    </div>

    <div class="flow-footer">
      <button class="button ghost" @click="$emit('back')"><ArrowLeft :size="16" /> 返回章节</button>
      <span>所有分析结果均可编辑</span>
      <button class="button primary" @click="$emit('next')">生成结构化剧本 <ArrowRight :size="16" /></button>
    </div>
  </section>
</template>
