<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowRight, BookOpen, CheckCircle2, FileText, LoaderCircle, Merge, Pencil, Scissors, UploadCloud } from 'lucide-vue-next'
import { parseProjectChapters } from '../api/projects'
import type { Project } from '../types'
import { parseChapters } from '../utils'

const props = defineProps<{ project: Project; projectId: string; backendConnected: boolean }>()
const emit = defineEmits<{ next: []; notify: [message: string] }>()
const isDragging = ref(false)
const isParsing = ref(false)
const selectedChapter = ref(0)
const parseSource = ref<'backend' | 'local' | ''>('')
const chapterContentEditor = ref<HTMLTextAreaElement | null>(null)

const wordCount = computed(() => props.project.rawText.replace(/\s/g, '').length)
const valid = computed(() => props.project.chapters.length >= 3)
const supportedExtensions = ['txt', 'md', 'docx']
type FileEncoding = 'UTF-8' | 'GB18030' | 'UTF-16LE' | 'UTF-16BE' | 'DOCX'

function chapterMetadata(content: string) {
  const sentences = content.split(/[。！？](?:[”’」』])?|\n/).map((sentence) => sentence.trim()).filter(Boolean)
  return {
    summary: sentences.slice(0, 2).join('。').slice(0, 120),
    keyEvents: sentences.slice(0, 3),
  }
}

function invalidateChapterDerivedData() {
  props.project.summary = ''
  props.project.genre = ''
  props.project.style = ''
  props.project.era = ''
  props.project.characters = []
  props.project.relationships = []
  props.project.scenes = []
  props.project.analysisStatus = 'pending'
  props.project.analysisMode = ''
  props.project.analysisError = ''
  props.project.analysisAttempts = 0
  props.project.generationStatus = 'pending'
  props.project.generationMode = ''
  props.project.generationError = ''
  props.project.generationAttempts = 0
  props.project.generationChapters = []
  parseSource.value = ''
}

function replaceChapters(chapters: Project['chapters']) {
  props.project.chapters = chapters
  invalidateChapterDerivedData()
}

function refreshChapterMetadata(index: number) {
  const chapter = props.project.chapters[index]
  if (!chapter) return
  Object.assign(chapter, chapterMetadata(chapter.content))
  invalidateChapterDerivedData()
}

function splitChapter() {
  const chapter = props.project.chapters[selectedChapter.value]
  const position = chapterContentEditor.value?.selectionStart ?? 0
  if (!chapter || position <= 0 || position >= chapter.content.length) {
    emit('notify', '请先把光标放在章节正文中需要拆分的位置')
    return
  }

  const firstContent = chapter.content.slice(0, position).trim()
  const secondContent = chapter.content.slice(position).trim()
  if (!firstContent || !secondContent) {
    emit('notify', '拆分位置前后都需要保留正文内容')
    return
  }

  chapter.content = firstContent
  Object.assign(chapter, chapterMetadata(firstContent))
  props.project.chapters.splice(selectedChapter.value + 1, 0, {
    id: `chapter-${Date.now()}`,
    title: `${chapter.title}（下）`,
    content: secondContent,
    ...chapterMetadata(secondContent),
  })
  selectedChapter.value += 1
  invalidateChapterDerivedData()
  emit('notify', '已按光标位置拆分章节')
}

function mergeNextChapter() {
  const chapter = props.project.chapters[selectedChapter.value]
  const nextChapter = props.project.chapters[selectedChapter.value + 1]
  if (!chapter || !nextChapter) {
    emit('notify', '当前章节后面没有可合并的章节')
    return
  }

  chapter.content = `${chapter.content.trim()}\n\n${nextChapter.content.trim()}`.trim()
  Object.assign(chapter, chapterMetadata(chapter.content))
  props.project.chapters.splice(selectedChapter.value + 1, 1)
  invalidateChapterDerivedData()
  emit('notify', `已将“${nextChapter.title}”合并到当前章节`)
}

async function detect() {
  if (isParsing.value) return
  isParsing.value = true

  try {
    if (props.backendConnected && props.projectId) {
      const result = await parseProjectChapters(props.projectId, props.project.rawText)
      replaceChapters(result.chapters)
      parseSource.value = 'backend'
      emit('notify', `后端已识别 ${result.chapter_count} 个章节${result.valid ? '' : '，至少需要 3 章'}`)
    } else {
      replaceChapters(parseChapters(props.project.rawText))
      parseSource.value = 'local'
      emit('notify', `本地已识别 ${props.project.chapters.length} 个章节`)
    }
  } catch {
    replaceChapters(parseChapters(props.project.rawText))
    parseSource.value = 'local'
    emit('notify', `后端解析失败，已使用本地规则识别 ${props.project.chapters.length} 个章节`)
  } finally {
    selectedChapter.value = 0
    isParsing.value = false
  }
}

function hasPrefix(bytes: Uint8Array, prefix: number[]) {
  return prefix.every((value, index) => bytes[index] === value)
}

function detectUtf16(bytes: Uint8Array) {
  const sample = bytes.slice(0, Math.min(bytes.length, 200))
  let evenZeroes = 0
  let oddZeroes = 0

  sample.forEach((value, index) => {
    if (value !== 0) return
    if (index % 2 === 0) evenZeroes += 1
    else oddZeroes += 1
  })

  if (oddZeroes > sample.length / 5) return 'utf-16le'
  if (evenZeroes > sample.length / 5) return 'utf-16be'
  return ''
}

function decodeText(bytes: Uint8Array, encoding: string) {
  return new TextDecoder(encoding, { fatal: true }).decode(bytes)
}

async function readPlainText(file: File): Promise<{ text: string; encoding: FileEncoding }> {
  const bytes = new Uint8Array(await file.arrayBuffer())

  if (hasPrefix(bytes, [0xff, 0xfe])) return { text: decodeText(bytes, 'utf-16le'), encoding: 'UTF-16LE' }
  if (hasPrefix(bytes, [0xfe, 0xff])) return { text: decodeText(bytes, 'utf-16be'), encoding: 'UTF-16BE' }

  const utf16Encoding = detectUtf16(bytes)
  if (utf16Encoding) {
    return {
      text: decodeText(bytes, utf16Encoding),
      encoding: utf16Encoding === 'utf-16le' ? 'UTF-16LE' : 'UTF-16BE',
    }
  }

  try {
    return { text: decodeText(bytes, 'utf-8'), encoding: 'UTF-8' }
  } catch {
    return { text: decodeText(bytes, 'gb18030'), encoding: 'GB18030' }
  }
}

async function readFileText(file: File, extension: string): Promise<{ text: string; encoding: FileEncoding }> {
  if (extension !== 'docx') return readPlainText(file)

  const mammoth = (await import('mammoth')).default
  return {
    text: (await mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() })).value,
    encoding: 'DOCX',
  }
}

async function handleFile(file?: File) {
  if (!file) return

  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  if (!supportedExtensions.includes(extension)) {
    emit('notify', '暂不支持该文件格式，请上传 .txt、.md 或 .docx 文件')
    return
  }

  try {
    const { text, encoding } = await readFileText(file, extension)

    if (!text.trim()) {
      emit('notify', '文件中没有可识别的文本内容')
      return
    }

    props.project.rawText = text
    props.project.filename = file.name
    props.project.genre = ''
    props.project.style = ''
    props.project.era = ''
    props.project.summary = ''
    props.project.characters = []
    props.project.relationships = []
    props.project.scenes = []
    props.project.analysisStatus = 'pending'
    props.project.analysisMode = ''
    props.project.analysisError = ''
    props.project.analysisAttempts = 0
    props.project.generationStatus = 'pending'
    props.project.generationMode = ''
    props.project.generationError = ''
    props.project.generationAttempts = 0
    props.project.generationChapters = []
    if (props.project.title === '未命名故事') props.project.title = file.name.replace(/\.(txt|md|docx)$/i, '')
    await detect()
    if (encoding !== 'UTF-8' && encoding !== 'DOCX') {
      emit('notify', `已按 ${encoding} 编码读取，并识别 ${props.project.chapters.length} 个章节`)
    }
  } catch {
    emit('notify', '文件解析失败，请确认文件未损坏或转换为 UTF-8 后重试')
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
          <span class="drop-hint">支持 .txt / .md / .docx，文本文件自动兼容常见中文编码</span>
        </div>
        <button class="button soft full" :disabled="isParsing" @click="detect">
          <LoaderCircle v-if="isParsing" class="spin" :size="16" />
          <BookOpen v-else :size="16" />
          {{ isParsing ? '正在识别章节…' : '重新识别章节' }}
        </button>
      </div>

      <div class="panel chapter-panel">
        <div class="panel-title">
          <div><BookOpen :size="17" /><b>章节识别结果</b></div>
          <span class="valid-badge" :class="{ invalid: !valid }">
            <CheckCircle2 :size="14" />{{ valid ? `结构有效${parseSource ? ` · ${parseSource === 'backend' ? '后端' : '本地'}` : ''}` : '至少需要 3 章' }}
          </span>
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
            <span class="chapter-info"><input v-model="chapter.title" @click.stop @change="invalidateChapterDerivedData" /><small>{{ chapter.content.length }} 字 · 已识别</small></span>
            <Pencil :size="14" />
          </button>
          <div v-if="!project.chapters.length" class="empty-state">
            <BookOpen :size="28" />
            <b>还没有识别到章节</b>
            <span>章节标题可使用“第一章”或“Chapter 1”等格式</span>
          </div>
        </div>
        <div v-if="project.chapters[selectedChapter]" class="chapter-preview chapter-boundary-editor">
          <div class="chapter-boundary-head">
            <span>章节正文与划分</span>
            <div>
              <button title="在正文光标位置拆分为两章" @click="splitChapter"><Scissors :size="13" /> 按光标拆分</button>
              <button :disabled="selectedChapter === project.chapters.length - 1" title="把下一章正文合并到当前章" @click="mergeNextChapter"><Merge :size="13" /> 合并下一章</button>
            </div>
          </div>
          <textarea
            ref="chapterContentEditor"
            v-model="project.chapters[selectedChapter].content"
            rows="8"
            @change="refreshChapterMetadata(selectedChapter)"
          ></textarea>
          <small>可直接编辑正文，或把光标放在新的章节边界后点击“按光标拆分”。</small>
        </div>
      </div>
    </div>

    <div class="flow-footer">
      <span><CheckCircle2 :size="15" /> {{ backendConnected ? '原文与章节将同步至后端' : '后端未连接，原文暂存于浏览器' }}</span>
      <button class="button primary" :disabled="!valid" @click="$emit('next')">确认章节，开始分析 <ArrowRight :size="16" /></button>
    </div>
  </section>
</template>
