import yaml from 'js-yaml'
import type { Chapter, Project, Scene } from './types'

export function parseChapters(text: string): Chapter[] {
  const pattern = /^(第[零一二三四五六七八九十百\d]+章[^\n。！？]{0,80}|Chapter\s+\d+[^\n.!?]{0,80})$/gim
  const matches = [...text.matchAll(pattern)]

  if (!matches.length) return []

  return matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length
    const end = matches[index + 1]?.index ?? text.length
    const content = text.slice(start, end).trim()
    const title = match[0].trim()
    const sentences = content.split(/[。！？](?:[”’」』])?|\n/).map((sentence) => sentence.trim()).filter(Boolean)
    return {
      id: `chapter-${index + 1}`,
      title,
      content,
      summary: sentences.slice(0, 2).join('。').slice(0, 120),
      keyEvents: sentences.slice(0, 3),
    }
  })
}

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

export function validateProjectScript(project: Project): string[] {
  const errors: string[] = []
  const chapterIds = new Set(project.chapters.map((chapter) => chapter.id))
  const chapterTitles = new Map(project.chapters.map((chapter) => [chapter.id, chapter.title]))
  const characterNames = new Set(project.characters.map((character) => character.name.trim()).filter(Boolean))
  const duplicateCharacterNames = [...new Set(project.characters
    .map((character) => character.name.trim())
    .filter((name, index, names) => name && names.indexOf(name) !== index))]
  const sceneIds = project.scenes.map((scene) => scene.id.trim()).filter(Boolean)
  const duplicateSceneIds = [...new Set(sceneIds.filter((id, index) => sceneIds.indexOf(id) !== index))]

  if (!project.title.trim()) errors.push('作品标题不能为空')
  if (!project.genre.trim()) errors.push('题材不能为空')
  if (!project.adaptationMode.trim()) errors.push('改编模式不能为空')
  if (!project.scriptType.trim()) errors.push('目标剧本类型不能为空')
  if (duplicateCharacterNames.length) errors.push(`人物名称重复：${duplicateCharacterNames.join('、')}`)
  project.characters.forEach((character, index) => {
    if (!character.name.trim() || !character.role.trim() || !character.description.trim()) {
      errors.push(`第 ${index + 1} 位人物字段不完整`)
    }
  })
  if (!project.scenes.length) errors.push('至少需要一个剧本场景')
  if (duplicateSceneIds.length) errors.push(`场景编号重复：${duplicateSceneIds.join('、')}`)

  project.scenes.forEach((scene, index) => {
    const label = scene.id.trim() || `第 ${index + 1} 场`
    const requiredFields = [
      [scene.id, '场景编号'],
      [scene.title, '场景标题'],
      [scene.location, '地点'],
      [scene.time, '时间'],
      [scene.atmosphere, '氛围'],
      [scene.sourceSummary, '来源剧情摘要'],
    ]
    requiredFields.forEach(([value, name]) => {
      if (!value.trim()) errors.push(`${label}：${name}不能为空`)
    })
    if (!chapterIds.has(scene.chapterId)) errors.push(`${label}：来源章节不存在`)
    else if (scene.sourceChapter !== chapterTitles.get(scene.chapterId)) errors.push(`${label}：来源章节标题与章节数据不一致`)
    if (!scene.actions.length || scene.actions.some((action) => !action.trim())) errors.push(`${label}：动作描述不能为空`)

    const duplicateCharacters = [...new Set(scene.characters.filter((name, itemIndex) => name && scene.characters.indexOf(name) !== itemIndex))]
    if (duplicateCharacters.length) errors.push(`${label}：出场人物重复：${duplicateCharacters.join('、')}`)
    const unknownCharacters = [...new Set(scene.characters.filter((name) => !characterNames.has(name)))]
    if (unknownCharacters.length) errors.push(`${label}：出场人物不在人物表：${unknownCharacters.join('、')}`)

    scene.dialogues.forEach((dialogue, dialogueIndex) => {
      if (!dialogue.character.trim() || !dialogue.emotion.trim() || !dialogue.line.trim()) {
        errors.push(`${label}：第 ${dialogueIndex + 1} 条对白字段不完整`)
      } else if (!scene.characters.includes(dialogue.character)) {
        errors.push(`${label}：对白人物“${dialogue.character}”不在本场出场人物中`)
      }
    })
  })
  return errors
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
