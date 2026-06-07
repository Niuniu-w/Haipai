<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Clipboard,
  Download,
  FileCode2,
  GripVertical,
  ListPlus,
  MessageSquareText,
  Plus,
  Save,
  Sparkles,
  Trash2,
  X,
} from 'lucide-vue-next'
import { exportProjectYaml, polishProjectScene, validateProjectYaml } from '../api/projects'
import type { Project, Scene } from '../types'
import { downloadText, nextSceneId, projectToYaml, syncGenerationStats, validateProjectScript } from '../utils'

const props = defineProps<{
  project: Project
  projectId: string
  backendConnected: boolean
  saveProject: () => Promise<boolean>
}>()
const emit = defineEmits<{ back: []; notify: [message: string]; save: [] }>()
const activeId = ref(props.project.scenes[0]?.id ?? '')
const rightTab = ref<'yaml' | 'source'>('yaml')
const polishOpen = ref(false)
const polishInstruction = ref('减少旁白，增加对白，让冲突更强烈')
const isExporting = ref(false)
const characterPickerOpen = ref(false)
const scenePendingDelete = ref<Scene | null>(null)
const collapsedChapterIds = ref(new Set<string>())
const isPolishing = ref(false)

const activeScene = computed(() => props.project.scenes.find((scene) => scene.id === activeId.value) ?? props.project.scenes[0])
const yamlText = computed(() => projectToYaml(props.project))
const validationErrors = computed(() => validateProjectScript(props.project))
const validationPassed = computed(() => validationErrors.value.length === 0)
const availableSceneCharacters = computed(() =>
  props.project.characters.filter((character) => !activeScene.value?.characters.includes(character.name)),
)
const groupedScenes = computed(() =>
  props.project.chapters.map((chapter) => ({
    chapter,
    scenes: props.project.scenes.filter((scene) => scene.chapterId === chapter.id),
  })),
)

function nextContentId() {
  const used = new Set(activeScene.value.content.map((item) => item.id))
  let number = activeScene.value.content.length + 1
  while (used.has(`${activeScene.value.id}-content-${number}`)) number += 1
  return `${activeScene.value.id}-content-${number}`
}

function addContent(type: 'action' | 'dialogue') {
  if (type === 'action') {
    activeScene.value.content.push({
      id: nextContentId(),
      type: 'action',
      action: '添加一条动作描述…',
    })
    return
  }
  const speaker = activeScene.value.characters[0]
  if (!speaker) {
    emit('notify', '请先为本场添加出场人物，再添加对白')
    return
  }
  activeScene.value.content.push({
    id: nextContentId(),
    type: 'dialogue',
    action: `${speaker}准备开口。`,
    character: speaker,
    emotion: '平静',
    line: '输入人物对白…',
  })
}

function addSceneCharacter(name: string) {
  if (!activeScene.value || activeScene.value.characters.includes(name)) return
  activeScene.value.characters.push(name)
  characterPickerOpen.value = false
  emit('notify', `已添加出场人物：${name}`)
}

function removeSceneCharacter(name: string) {
  if (activeScene.value.content.some((item) => item.type === 'dialogue' && item.character === name)) {
    emit('notify', `“${name}”仍有对白，请先调整或删除相关对白`)
    return
  }
  activeScene.value.characters = activeScene.value.characters.filter((character) => character !== name)
}

function toggleCharacterPicker() {
  if (!availableSceneCharacters.value.length) {
    emit('notify', props.project.characters.length ? '人物表中的人物都已在本场出场' : '请先在故事分析页添加人物')
    return
  }
  characterPickerOpen.value = !characterPickerOpen.value
}

function moveContent(index: number, direction: number) {
  const target = index + direction
  if (target < 0 || target >= activeScene.value.content.length) return
  const [item] = activeScene.value.content.splice(index, 1)
  activeScene.value.content.splice(target, 0, item)
}

function addScene() {
  const chapter = props.project.chapters.find((item) => item.id === activeScene.value?.chapterId)
    ?? props.project.chapters[0]
  if (!chapter) {
    emit('notify', '请先识别并保留至少一个章节')
    return
  }
  const sceneId = nextSceneId(props.project.scenes)
  const scene: Scene = {
    id: sceneId,
    chapterId: chapter.id,
    sourceChapter: chapter.title,
    title: '新场景',
    location: '待定地点',
    time: '日',
    atmosphere: '待定',
    characters: [],
    content: [{
      id: `${sceneId}-content-1`,
      type: 'action',
      action: '输入动作描述…',
    }],
    sourceSummary: chapter.summary,
  }
  props.project.scenes.push(scene)
  activeId.value = scene.id
  syncGenerationStats(props.project)
  emit('notify', '已添加新场景')
}

function requestRemoveScene() {
  if (props.project.scenes.length <= 1) {
    emit('notify', '项目至少需要保留一个场景')
    return
  }
  scenePendingDelete.value = activeScene.value
}

function confirmRemoveScene() {
  if (!scenePendingDelete.value) return
  const index = props.project.scenes.findIndex((scene) => scene.id === scenePendingDelete.value?.id)
  if (index < 0) return
  props.project.scenes.splice(index, 1)
  activeId.value = props.project.scenes[Math.max(0, index - 1)].id
  scenePendingDelete.value = null
  syncGenerationStats(props.project)
  emit('notify', '场景已删除')
}

function changeSceneChapter() {
  const chapter = props.project.chapters.find((item) => item.id === activeScene.value.chapterId)
  if (!chapter) return
  activeScene.value.sourceChapter = chapter.title
  activeScene.value.sourceSummary = chapter.summary
  syncGenerationStats(props.project)
  emit('notify', `场景已移动到“${chapter.title}”`)
}

function toggleChapter(chapterId: string) {
  const next = new Set(collapsedChapterIds.value)
  if (next.has(chapterId)) next.delete(chapterId)
  else next.add(chapterId)
  collapsedChapterIds.value = next
}

function copyYaml() {
  if (!validationPassed.value) {
    emit('notify', `结构校验失败：${validationErrors.value[0]}`)
    return
  }
  navigator.clipboard.writeText(yamlText.value)
  emit('notify', '完整 YAML 已复制')
}

async function downloadYaml() {
  if (!validationPassed.value) {
    emit('notify', `结构校验失败：${validationErrors.value[0]}`)
    return
  }
  isExporting.value = true
  try {
    if (props.backendConnected && props.projectId) {
      if (!await props.saveProject()) return
      const validation = await validateProjectYaml(props.projectId)
      if (!validation.valid) {
        emit('notify', `结构校验失败：${validation.errors[0]}`)
        return
      }
      downloadText(`${props.project.title}.yaml`, await exportProjectYaml(props.projectId))
      emit('notify', 'YAML 已导出')
    } else {
      downloadText(`${props.project.title}.yaml`, yamlText.value)
      emit('notify', 'YAML 已导出')
    }
  } catch {
    emit('notify', 'YAML 导出失败，请稍后重试')
  } finally {
    isExporting.value = false
  }
}

function applyLocalPolish(instruction: string) {
  if (/夜晚|夜景|改成夜/.test(instruction)) activeScene.value.time = '夜'
  if (/冲突|紧张|对峙/.test(instruction)) {
    activeScene.value.atmosphere = `${activeScene.value.atmosphere.replace(/、冲突升级$/, '')}、冲突升级`
    activeScene.value.content.push({
      id: nextContentId(),
      type: 'action',
      action: '人物的目标正面碰撞，现场气氛骤然收紧。',
    })
  }
  if (/对白|对话/.test(instruction)) {
    const speaker = activeScene.value.characters[0] ?? props.project.characters[0]?.name
    if (speaker) {
      if (!activeScene.value.characters.includes(speaker)) activeScene.value.characters.push(speaker)
      activeScene.value.content.push({
        id: nextContentId(),
        type: 'dialogue',
        action: `${speaker}直视对方，把压在心里的话说出口。`,
        character: speaker,
        emotion: '坚定',
        line: '把真正想说的话说出来。',
      })
    } else {
      activeScene.value.content.push({
        id: nextContentId(),
        type: 'action',
        action: '人物欲言又止，未说出口的话让气氛更紧张。',
      })
    }
  }
  if (!/夜晚|夜景|改成夜|冲突|紧张|对峙|对白|对话/.test(instruction)) {
    activeScene.value.content.push({
      id: nextContentId(),
      type: 'action',
      action: `强化当前场景的画面表达：${instruction || '优化节奏与人物行为。'}`,
    })
  }
}

async function applyPolish() {
  const instruction = polishInstruction.value.trim()
  if (!instruction || isPolishing.value) return
  isPolishing.value = true
  try {
    if (props.backendConnected && props.projectId) {
      if (!await props.saveProject()) return
      const result = await polishProjectScene(props.projectId, activeScene.value.id, instruction)
      Object.assign(activeScene.value, result.scene)
      emit('notify', '当前场景已润色')
    } else {
      applyLocalPolish(instruction)
      emit('notify', '当前场景已润色')
    }
  } catch {
    emit('notify', '场景润色失败，请稍后重试')
    return
  } finally {
    isPolishing.value = false
  }
  polishOpen.value = false
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
        <button class="button ghost small" @click="emit('save')"><Save :size="15" /> 保存</button>
        <button class="button ghost small" :disabled="!validationPassed" @click="copyYaml"><Clipboard :size="15" /> 复制 YAML</button>
        <button class="button primary small" :disabled="isExporting || !validationPassed" @click="downloadYaml"><Download :size="15" /> {{ isExporting ? '校验导出中…' : '导出剧本' }}</button>
      </div>
    </div>

    <div class="workspace-grid">
      <aside class="scene-sidebar">
        <div class="sidebar-head"><span>章节与场景</span><button @click="addScene"><Plus :size="15" /></button></div>
        <div class="scene-tree">
          <div v-for="group in groupedScenes" :key="group.chapter.id" class="tree-group">
            <div class="tree-chapter" role="button" tabindex="0" @click="toggleChapter(group.chapter.id)" @keydown.enter="toggleChapter(group.chapter.id)">
              <ChevronDown :size="13" :class="{ collapsed: collapsedChapterIds.has(group.chapter.id) }" />
              <span>{{ group.chapter.title }}</span><small>{{ group.scenes.length }}</small>
            </div>
            <button v-for="scene in collapsedChapterIds.has(group.chapter.id) ? [] : group.scenes" :key="scene.id" :class="{ active: scene.id === activeId }" @click="activeId = scene.id">
              <span class="scene-code">{{ scene.id }}</span>
              <span><b>{{ scene.title }}</b><small>{{ scene.location }} · {{ scene.time }}</small></span>
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
            <button class="icon-button danger" title="删除场景" @click="requestRemoveScene"><Trash2 :size="15" /></button>
            <button class="button magic small" @click="polishOpen = true"><Sparkles :size="15" /> 润色当前场景</button>
          </div>
        </div>

        <div class="editor-scroll">
          <label class="scene-title-input"><span>场景标题</span><input v-model="activeScene.title" /></label>
          <div class="scene-meta-grid four">
            <label><span>所属章节</span><select v-model="activeScene.chapterId" @change="changeSceneChapter"><option v-for="chapter in project.chapters" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option></select></label>
            <label><span>地点</span><input v-model="activeScene.location" /></label>
            <label><span>时间</span><input v-model="activeScene.time" /></label>
            <label><span>氛围</span><input v-model="activeScene.atmosphere" /></label>
          </div>

          <div class="editor-section">
            <div class="editor-section-title"><span>出场人物</span><button @click="toggleCharacterPicker"><Plus :size="13" /> 添加</button></div>
            <div v-if="characterPickerOpen" class="character-picker">
              <button v-for="character in availableSceneCharacters" :key="character.id" @click="addSceneCharacter(character.name)">
                {{ character.name }} · {{ character.role }}
              </button>
            </div>
            <div class="character-tags">
              <span v-for="name in activeScene.characters" :key="name">{{ name }}<button :title="`移除 ${name}`" @click="removeSceneCharacter(name)"><X :size="11" /></button></span>
            </div>
          </div>

          <div class="editor-section">
            <div class="editor-section-title">
              <span>剧本内容 · 按演出顺序</span>
              <div class="content-add-actions">
                <button @click="addContent('action')"><Plus :size="13" /> 添加动作</button>
                <button @click="addContent('dialogue')"><MessageSquareText :size="13" /> 添加对白</button>
              </div>
            </div>
            <div class="content-list">
              <div v-for="(item, index) in activeScene.content" :key="item.id" class="content-row" :class="item.type">
                <GripVertical :size="15" />
                <div class="row-move-actions">
                  <button title="上移内容" :disabled="index === 0" @click="moveContent(index, -1)"><ArrowUp :size="12" /></button>
                  <button title="下移内容" :disabled="index === activeScene.content.length - 1" @click="moveContent(index, 1)"><ArrowDown :size="12" /></button>
                </div>
                <span class="content-index">{{ String(index + 1).padStart(2, '0') }}</span>
                <div class="content-fields">
                  <div class="content-kind">{{ item.type === 'dialogue' ? '对白与动作' : '动作' }}</div>
                  <label class="content-action">
                    <span>{{ item.type === 'dialogue' ? '对白对应动作' : '动作描述' }}</span>
                    <textarea v-model="item.action" rows="2"></textarea>
                  </label>
                  <div v-if="item.type === 'dialogue'" class="dialogue-fields">
                    <div>
                      <select v-model="item.character" class="speaker">
                        <option v-for="name in activeScene.characters" :key="name" :value="name">{{ name }}</option>
                      </select>
                      <input v-model="item.emotion" class="emotion" placeholder="情绪" />
                    </div>
                    <label><span>人物对白</span><textarea v-model="item.line" rows="2"></textarea></label>
                  </div>
                </div>
                <button class="content-remove" title="删除内容" @click="activeScene.content.splice(index, 1)"><X :size="13" /></button>
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
        <div class="validation" :class="{ invalid: !validationPassed }" :title="validationErrors.join('\n')">
          <CheckCircle2 v-if="validationPassed" :size="14" />
          <CircleAlert v-else :size="14" />
          <span>{{ validationPassed ? '结构校验通过' : `结构校验失败：${validationErrors[0]}` }}</span>
          <small>{{ validationPassed ? `${project.scenes.length} 场` : `${validationErrors.length} 项` }}</small>
        </div>
        <pre v-if="rightTab === 'yaml'" class="yaml-preview">{{ yamlText }}</pre>
        <div v-else class="source-preview"><span>{{ activeScene.sourceChapter }}</span><p>{{ project.chapters.find((chapter) => chapter.id === activeScene.chapterId)?.content }}</p></div>
        <div class="preview-footer"><span>YAML · UTF-8</span><button :disabled="!validationPassed" @click="copyYaml"><Clipboard :size="13" /> 复制</button></div>
      </aside>
    </div>

    <Transition name="modal">
      <div v-if="polishOpen" class="modal-backdrop" @click.self="polishOpen = false">
        <div class="polish-modal">
          <button class="modal-close" @click="polishOpen = false"><X :size="17" /></button>
          <div class="generate-mark small"><Sparkles :size="18" /></div>
          <span class="section-index">SCENE REWRITE</span>
          <h3>调整当前场景</h3>
          <p>描述你希望调整的效果，我们会保持剧情事实并优化当前场景。</p>
          <textarea v-model="polishInstruction" rows="4"></textarea>
          <div class="prompt-chips"><button @click="polishInstruction = '让冲突更强烈'">冲突更强烈</button><button @click="polishInstruction = '减少旁白，增加对白'">增加对白</button><button @click="polishInstruction = '保持剧情不变，改成夜晚'">改成夜晚</button></div>
          <button class="button primary full" :disabled="isPolishing || !polishInstruction.trim()" @click="applyPolish"><Sparkles :size="15" /> {{ isPolishing ? '润色中…' : '润色当前场景' }}</button>
        </div>
      </div>
    </Transition>

    <Transition name="modal">
      <div v-if="scenePendingDelete" class="modal-backdrop" @click.self="scenePendingDelete = null">
        <div class="confirm-modal">
          <div class="confirm-icon"><Trash2 :size="18" /></div>
          <h3>删除场景“{{ scenePendingDelete.title }}”？</h3>
          <p>该场景中的剧本内容和编辑信息都会被删除，此操作无法撤销。</p>
          <div class="confirm-actions">
            <button class="button ghost" @click="scenePendingDelete = null">取消</button>
            <button class="button danger-fill" @click="confirmRemoveScene">确认删除</button>
          </div>
        </div>
      </div>
    </Transition>
  </section>
</template>
