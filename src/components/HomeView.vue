<script setup lang="ts">
import { ArrowRight, BookOpenText, Clapperboard, FileText, FolderOpen, Play, Sparkles, Trash2, WandSparkles } from 'lucide-vue-next'
import type { ProjectSummary } from '../api/projects'
import type { Project } from '../types'
import { formatUpdatedAt } from '../utils'

defineProps<{ project: Project; projects: ProjectSummary[] }>()
defineEmits<{ start: []; demo: []; continue: []; open: [projectId: string]; remove: [projectId: string] }>()
</script>

<template>
  <section class="home-view">
    <div class="hero-noise"></div>
    <div class="hero-copy">
      <div class="eyebrow"><Sparkles :size="14" /> AI 小说剧本工坊 · DEMO</div>
      <h1>让故事从纸上<br /><em>走进镜头。</em></h1>
      <p class="hero-lead">导入小说，理清人物与情节，让 AI 和你一起完成第一版剧本。</p>
      <div class="hero-actions">
        <button class="button primary large" @click="$emit('start')">开始改编 <ArrowRight :size="17" /></button>
        <button class="button ghost large" @click="$emit('demo')"><Play :size="16" fill="currentColor" /> 体验示例</button>
      </div>
      <div class="hero-note"><span></span>无需 API Key，示例流程可完整体验</div>
    </div>

    <div class="hero-visual">
      <div class="script-page">
        <div class="paper-kicker">SCENE 01 · NIGHT</div>
        <h3>雨夜的匿名信</h3>
        <p class="scene-heading">内景 · 留声咖啡馆 · 夜</p>
        <p>雨水顺着玻璃蜿蜒而下。林墨推开门，周岚只朝角落的桌子看了一眼。</p>
        <div class="dialogue-block">
          <strong>林墨</strong>
          <span>这封信，是留给我的？</span>
        </div>
        <div class="paper-line short"></div>
        <div class="paper-line"></div>
        <div class="paper-line mid"></div>
        <div class="page-stamp">AI DRAFT</div>
      </div>
      <div class="floating-card card-one"><BookOpenText :size="17" /><span><b>4</b> 个章节已识别</span></div>
      <div class="floating-card card-two"><WandSparkles :size="17" /><span>人物关系提取完成</span></div>
      <div class="visual-orbit"></div>
    </div>

    <div class="process-strip">
      <div class="process-intro"><span>从原著到剧本</span><strong>四步完成第一次改编</strong></div>
      <div class="process-item"><i>01</i><FileText :size="20" /><div><b>导入原著</b><span>智能识别章节</span></div></div>
      <div class="process-arrow">→</div>
      <div class="process-item"><i>02</i><Sparkles :size="20" /><div><b>理解故事</b><span>提取人物与情节</span></div></div>
      <div class="process-arrow">→</div>
      <div class="process-item"><i>03</i><WandSparkles :size="20" /><div><b>生成剧本</b><span>逐章结构化改编</span></div></div>
      <div class="process-arrow">→</div>
      <div class="process-item"><i>04</i><Clapperboard :size="20" /><div><b>编辑导出</b><span>实时预览 YAML</span></div></div>
    </div>

    <button v-if="project.scenes.length" class="recent-project" @click="$emit('continue')">
      <span class="recent-icon"><Clapperboard :size="19" /></span>
      <span><small>继续最近项目</small><b>《{{ project.title }}》</b></span>
      <span class="recent-meta">{{ project.chapters.length }} 章 · {{ project.scenes.length }} 场 · {{ formatUpdatedAt(project.updatedAt) }}</span>
      <ArrowRight :size="17" />
    </button>

    <section v-if="projects.length" class="project-history">
      <div class="history-head"><span>后端项目</span><small>已保存 {{ projects.length }} 个项目</small></div>
      <div class="history-list">
        <article v-for="item in projects" :key="item.id" class="history-item">
          <button class="history-open" @click="$emit('open', item.id)">
            <FolderOpen :size="17" />
            <span><b>《{{ item.title }}》</b><small>{{ item.chapter_count }} 章 · {{ item.scene_count }} 场 · {{ formatUpdatedAt(item.updated_at) }}</small></span>
          </button>
          <button class="history-remove" title="删除后端项目" @click="$emit('remove', item.id)"><Trash2 :size="14" /></button>
        </article>
      </div>
    </section>
  </section>
</template>
