<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowRight, BookOpen, CheckCircle2, FileText, Pencil, UploadCloud } from 'lucide-vue-next'
import type { Project } from '../types'
import { parseChapters } from '../utils'

const props = defineProps<{ project: Project }>()
const emit = defineEmits<{ next: []; notify: [message: string] }>()
const isDragging = ref(false)
const selectedChapter = ref(0)

const wordCount = computed(() => props.project.rawText.replace(/\s/g, '').length)
const valid = computed(() => props.project.chapters.length >= 3)
const supportedExtensions = ['txt', 'md', 'docx']

function detect() {
  props.project.chapters = parseChapters(props.project.rawText)
  selectedChapter.value = 0
  emit('notify', `已识别 ${props.project.chapters.length} 个章节`)
}

async function readFileText(file: File, extension: string) {
  if (extension !== 'docx') return file.text()

  const mammoth = (await import('mammoth')).default
  return (await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })).value
}

async function handleFile(file?: File) {
  if (!file) return

  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!supportedExtensions.includes(extension)) {
    emit('notify', '暂不支持该文件格式，请上传 .txt、.md 或 .docx 文件')
    return
  }

  try {
    const text = await readFileText(file, extension)

    if (!text.trim()) {
      emit('notify', '文件中没有可识别的文本内容')
      return
    }

    props.project.rawText = text
    props.project.filename = file.name
    if (props.project.title === '未命名故事') props.project.title = file.name.replace(/\.(txt|md|docx)$/i, '')
    detect()
  } catch {
    emit('notify', '文件解析失败，请确认文件未损坏且格式正确')
  }
}
</script>

<template>
  <section class="flow-page import-page">
    <div class="flow-heading">
      <div>
        <span class="section-index">01 / IMPORT</span>
        <h2>先从你的故事开始</h2>
        <p>粘贴或上传小说，我们会先帮你识别章节结构。</p>
      </div>
      <div class="heading-stats">
        <div><span>{{ wordCount.toLocaleString() }}</span><small>字数</small></div>
        <div><span>{{ project.chapters.length }}</span><small>识别章节</small></div>
      </div>
    </div>

    <div class="import-grid">
      <div class="panel source-panel">
        <div class="panel-title">
          <div><FileText :size="17" /><b>小说原文</b><span v-if="project.filename" class="file-pill">{{ project.filename }}</span></div>
          <label class="text-button">
            <UploadCloud :size="15" /> 上传文件
            <input
              type="file"
              accept=".txt,.md,.docx,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              hidden
              @change="handleFile(($event.target as HTMLInputElement).files?.[0])"
            />
          </label>
        </div>
        <input v-model="project.title" class="title-input" placeholder="输入作品标题" />
        <div
          class="text-drop"
          :class="{ dragging: isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="isDragging = false; handleFile($event.dataTransfer?.files[0])"
        >
          <textarea v-model="project.rawText" placeholder="在这里粘贴至少包含三个章节的小说原文…" @blur="detect"></textarea>
          <span class="drop-hint">支持 .txt / .md / .docx，拖拽文件到此处也可以</span>
        </div>
        <button class="button soft full" @click="detect"><BookOpen :size="16" /> 重新识别章节</button>
      </div>

      <div class="panel chapter-panel">
        <div class="panel-title">
          <div><BookOpen :size="17" /><b>章节识别结果</b></div>
          <span class="valid-badge" :class="{ invalid: !valid }"><CheckCircle2 :size="14" />{{ valid ? '结构有效' : '至少需要 3 章' }}</span>
        </div>
        <div class="chapter-list">
          <button
            v-for="(chapter, index) in project.chapters"
            :key="chapter.id"
            class="chapter-row"
            :class="{ active: selectedChapter === index }"
            @click="selectedChapter = index"
          >
            <span class="chapter-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="chapter-info"><input v-model="chapter.title" @click.stop /><small>{{ chapter.content.length }} 字 · 已识别</small></span>
            <Pencil :size="14" />
          </button>
          <div v-if="!project.chapters.length" class="empty-state">
            <BookOpen :size="28" />
            <b>还没有识别到章节</b>
            <span>章节标题可使用“第一章”或“Chapter 1”等格式</span>
          </div>
        </div>
        <div v-if="project.chapters[selectedChapter]" class="chapter-preview">
          <span>章节开头预览</span>
          <p>{{ project.chapters[selectedChapter].content.slice(0, 125) }}…</p>
        </div>
      </div>
    </div>

    <div class="flow-footer">
      <span><CheckCircle2 :size="15" /> 原文仅保存在你的浏览器中</span>
      <button class="button primary" :disabled="!valid" @click="$emit('next')">确认章节，开始分析 <ArrowRight :size="16" /></button>
    </div>
  </section>
</template>
