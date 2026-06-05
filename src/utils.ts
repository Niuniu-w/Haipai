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
