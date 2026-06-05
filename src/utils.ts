import yaml from 'js-yaml'
import type { Chapter, Project, Scene } from './types'

export function parseChapters(text: string): Chapter[] {
  const pattern = /^(第[零一二三四五六七八九十百\d]+章[^\n]*|Chapter\s+\d+[^\n]*)$/gim
  const matches = [...text.matchAll(pattern)]

  if (!matches.length) return []

  return matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length
    const end = matches[index + 1]?.index ?? text.length
    const content = text.slice(start, end).trim()
    const title = match[0].trim()
    return {
      id: `chapter-${index + 1}`,
      title,
      content,
      summary: chapterSummaries[index] ?? content.slice(0, 80),
      keyEvents: chapterEvents[index] ?? ['识别章节核心冲突', '推进人物关系'],
    }
  })
}

const chapterSummaries = [
  '记者林墨在雨夜收到匿名信，十二年前的临江大桥事故重新进入他的视野。',
  '林墨与苏禾找到被修改的档案记录，并从陈望手中发现关键底片。',
  '底片揭开事故背后的工程车，周岚也坦白了自己寄出匿名信的原因。',
  '林墨拒绝高启明的交易，在天亮前发布报道，让迟到的真相重见天日。',
]

const chapterEvents = [
  ['林墨收到匿名信', '黑伞人监视咖啡馆', '旧事故疑点重现'],
  ['事故底片失踪', '借阅记录被篡改', '陈望交出底片'],
  ['工程车证据出现', '周岚坦白身份', '众人遭遇威胁'],
  ['高启明试图交易', '林墨录下电话', '调查报道发布'],
]

export function projectToYaml(project: Project): string {
  const output = {
    title: project.title,
    genre: project.genre,
    adaptation_mode: project.adaptationMode,
    script_type: project.scriptType,
    characters: project.characters.map((character) => ({
      name: character.name,
      role: character.role,
      description: character.description,
    })),
    scenes: project.scenes.map((scene) => sceneToOutput(scene)),
  }
  return yaml.dump(output, { noRefs: true, lineWidth: 100, quotingType: '"', forceQuotes: false })
}

export function buildScenes(chapters: Chapter[]): Scene[] {
  const locations = ['咖啡馆', '报社档案室', '临江大桥下', '编辑部']
  const times = ['夜 / 暴雨', '深夜', '午夜', '黎明前']
  return chapters.map((chapter, index) => ({
    id: `SC-${String(index + 1).padStart(2, '0')}`,
    chapterId: chapter.id,
    sourceChapter: chapter.title,
    title: chapter.title.replace(/^(第[零一二三四五六七八九十百\d]+章|Chapter\s+\d+)/i, '').trim() || `场景 ${index + 1}`,
    location: locations[index] ?? '待定地点',
    time: times[index] ?? '日',
    atmosphere: index === chapters.length - 1 ? '坚定、迎向光亮' : '克制、暗藏不安',
    characters: index === 0 ? ['林墨', '周岚'] : index === 1 ? ['林墨', '苏禾'] : ['林墨', '苏禾', '周岚'],
    actions: [
      chapter.content.split(/[。！？]/).filter(Boolean)[0]?.trim() + '。',
      chapter.content.split(/[。！？]/).filter(Boolean)[1]?.trim() + '。',
    ].filter((line) => line !== 'undefined。'),
    dialogues: [
      {
        id: `dialogue-${index + 1}`,
        character: '林墨',
        emotion: index === chapters.length - 1 ? '坚定' : '警觉',
        line: index === chapters.length - 1 ? '有些故事迟到了，但不会消失。' : '我需要知道这里发生过什么。',
      },
    ],
    sourceSummary: chapter.summary,
  }))
}

function sceneToOutput(scene: Scene) {
  return {
    id: scene.id,
    source_chapter: scene.sourceChapter,
    title: scene.title,
    location: scene.location,
    time: scene.time,
    atmosphere: scene.atmosphere,
    characters: scene.characters,
    actions: scene.actions,
    dialogues: scene.dialogues.map(({ character, emotion, line }) => ({ character, emotion, line })),
    source_summary: scene.sourceSummary,
  }
}

export function downloadText(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/yaml;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}
