<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  Download,
  FileCode2,
  GripVertical,
  ListPlus,
  MessageSquareText,
  MoreHorizontal,
  Plus,
  RotateCw,
  Save,
  Sparkles,
  Trash2,
  X,
} from 'lucide-vue-next'
import type { Project, Scene } from '../types'
import { downloadText, projectToYaml } from '../utils'

const props = defineProps<{ project: Project }>()
const emit = defineEmits<{ back: []; notify: [message: string] }>()
const activeId = ref(props.project.scenes[0]?.id ?? '')
const rightTab = ref<'yaml' | 'source'>('yaml')
const polishOpen = ref(false)
const polishInstruction = ref('减少旁白，增加对白，让冲突更强烈')

const activeScene = computed(() => props.project.scenes.find((scene) => scene.id === activeId.value) ?? props.project.scenes[0])
const yamlText = computed(() => projectToYaml(props.project))
const groupedScenes = computed(() =>
  props.project.chapters.map((chapter) => ({
    chapter,
    scenes: props.project.scenes.filter((scene) => scene.chapterId === chapter.id),
  })),
)

function addAction() {
  activeScene.value.actions.push('添加一条动作描述…')
}

function addDialogue() {
  activeScene.value.dialogues.push({
    id: `dialogue-${Date.now()}`,
    character: activeScene.value.characters[0] ?? '角色',
    emotion: '平静',
    line: '输入人物对白…',
  })
}

function addScene() {
  const chapter = props.project.chapters[props.project.chapters.length - 1]
  const scene: Scene = {
    id: `SC-${String(props.project.scenes.length + 1).padStart(2, '0')}`,
    chapterId: chapter.id,
    sourceChapter: chapter.title,
    title: '新场景',
    location: '待定地点',
    time: '日',
    atmosphere: '待定',
    characters: [],
    actions: ['输入动作描述…'],
    dialogues: [],
    sourceSummary: chapter.summary,
  }
  props.project.scenes.push(scene)
  activeId.value = scene.id
  emit('notify', '已添加新场景')
}

function removeScene() {
  if (props.project.scenes.length <= 1) return
  const index = props.project.scenes.findIndex((scene) => scene.id === activeId.value)
  props.project.scenes.splice(index, 1)
  activeId.value = props.project.scenes[Math.max(0, index - 1)].id
}

function copyYaml() {
  navigator.clipboard.writeText(yamlText.value)
  emit('notify', '完整 YAML 已复制')
}

function downloadYaml() {
  downloadText(`${props.project.title}.yaml`, yamlText.value)
  emit('notify', 'YAML 文件已导出')
}

function applyPolish() {
  activeScene.value.atmosphere = `${activeScene.value.atmosphere}、冲突升级`
  activeScene.value.actions.push('两人短暂对峙，空气里的沉默比回答更有分量。')
  polishOpen.value = false
  emit('notify', 'AI 已根据指令润色当前场景')
}

function moveScene(direction: number) {
  const index = props.project.scenes.findIndex((scene) => scene.id === activeId.value)
  const target = index + direction
  if (target < 0 || target >= props.project.scenes.length) return
  const [scene] = props.project.scenes.splice(index, 1)
  props.project.scenes.splice(target, 0, scene)
}
</script>

<template>
  <section class="workspace">
    <div class="workspace-toolbar">
      <div class="workspace-title">
        <button class="icon-button" @click="$emit('back')"><ArrowLeft :size="17" /></button>
        <div><span>剧本工作台</span><h2>《{{ project.title }}》</h2></div>
        <span class="draft-pill">DRAFT 01</span>
      </div>
      <div class="toolbar-actions">
        <button class="button ghost small" @click="emit('notify', '项目已保存到浏览器')"><Save :size="15" /> 保存</button>
        <button class="button ghost small" @click="copyYaml"><Clipboard :size="15" /> 复制 YAML</button>
        <button class="button primary small" @click="downloadYaml"><Download :size="15" /> 导出剧本</button>
      </div>
    </div>

    <div class="workspace-grid">
      <aside class="scene-sidebar">
        <div class="sidebar-head"><span>章节与场景</span><button @click="addScene"><Plus :size="15" /></button></div>
        <div class="scene-tree">
          <div v-for="group in groupedScenes" :key="group.chapter.id" class="tree-group">
            <div class="tree-chapter"><ChevronDown :size="13" /><span>{{ group.chapter.title }}</span><small>{{ group.scenes.length }}</small></div>
            <button v-for="scene in group.scenes" :key="scene.id" :class="{ active: scene.id === activeId }" @click="activeId = scene.id">
              <span class="scene-code">{{ scene.id }}</span>
              <span><b>{{ scene.title }}</b><small>{{ scene.location }} · {{ scene.time }}</small></span>
              <MoreHorizontal :size="14" />
            </button>
          </div>
        </div>
        <button class="add-scene-button" @click="addScene"><ListPlus :size="15" /> 添加场景</button>
      </aside>

      <main v-if="activeScene" class="scene-editor">
        <div class="editor-head">
          <div><span class="scene-code">{{ activeScene.id }}</span><span class="source-chip">{{ activeScene.sourceChapter }}</span></div>
          <div>
            <button class="icon-button" title="上移" @click="moveScene(-1)"><ArrowUp :size="15" /></button>
            <button class="icon-button" title="下移" @click="moveScene(1)"><ArrowDown :size="15" /></button>
            <button class="icon-button danger" title="删除场景" @click="removeScene"><Trash2 :size="15" /></button>
            <button class="button magic small" @click="polishOpen = true"><Sparkles :size="15" /> AI 润色</button>
          </div>
        </div>

        <div class="editor-scroll">
          <label class="scene-title-input"><span>场景标题</span><input v-model="activeScene.title" /></label>
          <div class="scene-meta-grid">
            <label><span>地点</span><input v-model="activeScene.location" /></label>
            <label><span>时间</span><input v-model="activeScene.time" /></label>
            <label><span>氛围</span><input v-model="activeScene.atmosphere" /></label>
          </div>

          <div class="editor-section">
            <div class="editor-section-title"><span>出场人物</span><button><Plus :size="13" /> 添加</button></div>
            <div class="character-tags"><span v-for="name in activeScene.characters" :key="name">{{ name }}<X :size="11" /></span></div>
          </div>

          <div class="editor-section">
            <div class="editor-section-title"><span>动作描述</span><button @click="addAction"><Plus :size="13" /> 添加动作</button></div>
            <div class="action-list">
              <div v-for="(_, index) in activeScene.actions" :key="index" class="action-row">
                <GripVertical :size="15" /><span>{{ String(index + 1).padStart(2, '0') }}</span><textarea v-model="activeScene.actions[index]" rows="2"></textarea>
                <button @click="activeScene.actions.splice(index, 1)"><X :size="13" /></button>
              </div>
            </div>
          </div>

          <div class="editor-section">
            <div class="editor-section-title"><span>人物对白</span><button @click="addDialogue"><Plus :size="13" /> 添加对白</button></div>
            <div class="dialogue-list">
              <div v-for="(dialogue, index) in activeScene.dialogues" :key="dialogue.id" class="dialogue-row">
                <GripVertical :size="15" />
                <div class="dialogue-fields">
                  <div><input v-model="dialogue.character" class="speaker" /><input v-model="dialogue.emotion" class="emotion" /></div>
                  <textarea v-model="dialogue.line" rows="2"></textarea>
                </div>
                <button @click="activeScene.dialogues.splice(index, 1)"><X :size="13" /></button>
              </div>
            </div>
          </div>

          <div class="editor-section source-summary">
            <div class="editor-section-title"><span>来源剧情摘要</span><CheckCircle2 :size="14" /></div>
            <textarea v-model="activeScene.sourceSummary" rows="3"></textarea>
          </div>
        </div>
      </main>

      <aside class="preview-panel">
        <div class="preview-tabs">
          <button :class="{ active: rightTab === 'yaml' }" @click="rightTab = 'yaml'"><FileCode2 :size="14" /> YAML 预览</button>
          <button :class="{ active: rightTab === 'source' }" @click="rightTab = 'source'"><MessageSquareText :size="14" /> 原文对照</button>
        </div>
        <div class="validation"><CheckCircle2 :size="14" /><span>结构校验通过</span><small>{{ project.scenes.length }} 场</small></div>
        <pre v-if="rightTab === 'yaml'" class="yaml-preview">{{ yamlText }}</pre>
        <div v-else class="source-preview"><span>{{ activeScene.sourceChapter }}</span><p>{{ project.chapters.find((chapter) => chapter.id === activeScene.chapterId)?.content }}</p></div>
        <div class="preview-footer"><span>YAML · UTF-8</span><button @click="copyYaml"><Clipboard :size="13" /> 复制</button></div>
      </aside>
    </div>

    <Transition name="modal">
      <div v-if="polishOpen" class="modal-backdrop" @click.self="polishOpen = false">
        <div class="polish-modal">
          <button class="modal-close" @click="polishOpen = false"><X :size="17" /></button>
          <div class="generate-mark small"><Sparkles :size="18" /></div>
          <span class="section-index">AI SCENE REWRITE</span>
          <h3>想怎样调整这个场景？</h3>
          <p>AI 只会修改当前场景，不影响其他章节。</p>
          <textarea v-model="polishInstruction" rows="4"></textarea>
          <div class="prompt-chips"><button @click="polishInstruction = '让冲突更强烈'">冲突更强烈</button><button @click="polishInstruction = '减少旁白，增加对白'">增加对白</button><button @click="polishInstruction = '保持剧情不变，改成夜晚'">改成夜晚</button></div>
          <button class="button primary full" @click="applyPolish"><Sparkles :size="15" /> 应用 AI 润色</button>
        </div>
      </div>
    </Transition>
  </section>
</template>
