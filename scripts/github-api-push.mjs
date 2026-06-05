#!/usr/bin/env node

import { readFile, readdir } from 'node:fs/promises'
import { extname, join, relative, resolve, sep } from 'node:path'

const config = {
  owner: process.env.GITHUB_OWNER,
  repo: process.env.GITHUB_REPO,
  token: process.env.GITHUB_TOKEN,
  baseBranch: process.env.GITHUB_BASE_BRANCH || 'main',
  branch: process.env.GITHUB_BRANCH || 'feat/initial-storyforge-demo',
  commitMessage: process.env.GITHUB_COMMIT_MESSAGE || 'feat: initialize runnable StoryForge demo',
  prTitle: process.env.GITHUB_PR_TITLE || 'feat: initialize runnable StoryForge demo',
  createPullRequest: process.env.GITHUB_CREATE_PR !== 'false',
  root: resolve(process.cwd()),
}

const ignoredDirectories = new Set(['.git', 'node_modules', 'dist', '.idea', '.vscode'])
const ignoredFiles = new Set(['.DS_Store'])
const binaryExtensions = new Set([
  '.avif',
  '.gif',
  '.ico',
  '.jpeg',
  '.jpg',
  '.mov',
  '.mp3',
  '.mp4',
  '.pdf',
  '.png',
  '.webp',
  '.zip',
])

validateConfig()

const apiBase = `https://api.github.com/repos/${config.owner}/${config.repo}`
const headers = {
  Accept: 'application/vnd.github+json',
  Authorization: `Bearer ${config.token}`,
  'X-GitHub-Api-Version': '2022-11-28',
  'User-Agent': 'storyforge-github-api-push',
}

async function github(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers: {
      ...headers,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    const details = data?.message || `${response.status} ${response.statusText}`
    const error = new Error(`GitHub API 请求失败：${details}`)
    error.status = response.status
    throw error
  }

  return data
}

async function getBranchSha(branch) {
  try {
    const data = await github(`/git/ref/heads/${encodeURIComponent(branch)}`)
    return data.object.sha
  } catch (error) {
    if (error.status !== 404) throw error
    return null
  }
}

async function getRepository() {
  return github('')
}

async function ensureBaseBranch(repository) {
  let baseSha = await getBranchSha(config.baseBranch)
  if (baseSha) return baseSha

  const defaultSha = await getBranchSha(repository.default_branch)
  if (defaultSha) {
    await github('/git/refs', {
      method: 'POST',
      body: JSON.stringify({
        ref: `refs/heads/${config.baseBranch}`,
        sha: defaultSha,
      }),
    })
    return defaultSha
  }

  console.log(`仓库为空，正在创建 ${config.baseBranch} 初始化提交…`)
  await github('/contents/README.md', {
    method: 'PUT',
    body: JSON.stringify({
      message: 'chore: initialize repository for PR workflow',
      content: Buffer.from(
        '# Haipai\n\nThis repository is initialized for a pull-request-based delivery workflow.\n',
      ).toString('base64'),
    }),
  })

  baseSha = await getBranchSha(config.baseBranch)
  if (!baseSha) throw new Error(`初始化后仍未找到 ${config.baseBranch} 分支，请检查仓库默认分支设置。`)
  return baseSha
}

async function ensureFeatureBranch(baseSha) {
  const existingSha = await getBranchSha(config.branch)
  if (existingSha) return existingSha

  await github('/git/refs', {
    method: 'POST',
    body: JSON.stringify({
      ref: `refs/heads/${config.branch}`,
      sha: baseSha,
    }),
  })
  return baseSha
}

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const files = []

  for (const entry of entries) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue
    if (entry.isFile() && ignoredFiles.has(entry.name)) continue

    const absolutePath = join(directory, entry.name)
    if (entry.isDirectory()) files.push(...(await collectFiles(absolutePath)))
    if (entry.isFile()) files.push(absolutePath)
  }

  return files
}

async function createBlob(filePath) {
  const bytes = await readFile(filePath)
  const isBinary = binaryExtensions.has(extname(filePath).toLowerCase())
  const content = isBinary ? bytes.toString('base64') : bytes.toString('utf8')
  const encoding = isBinary ? 'base64' : 'utf-8'
  const blob = await github('/git/blobs', {
    method: 'POST',
    body: JSON.stringify({ content, encoding }),
  })

  return {
    path: relative(config.root, filePath).split(sep).join('/'),
    mode: '100644',
    type: 'blob',
    sha: blob.sha,
  }
}

async function createCommit(parentSha, tree) {
  const parentCommit = await github(`/git/commits/${parentSha}`)
  const createdTree = await github('/git/trees', {
    method: 'POST',
    body: JSON.stringify({
      base_tree: parentCommit.tree.sha,
      tree,
    }),
  })

  return github('/git/commits', {
    method: 'POST',
    body: JSON.stringify({
      message: config.commitMessage,
      tree: createdTree.sha,
      parents: [parentSha],
    }),
  })
}

async function updateBranch(commitSha) {
  return github(`/git/refs/heads/${encodeURIComponent(config.branch)}`, {
    method: 'PATCH',
    body: JSON.stringify({ sha: commitSha, force: false }),
  })
}

async function createPullRequest() {
  const existing = await github(
    `/pulls?state=open&head=${encodeURIComponent(`${config.owner}:${config.branch}`)}&base=${encodeURIComponent(config.baseBranch)}`,
  )
  if (existing.length) return existing[0]

  const body = `## 功能描述

初始化可运行的织幕 StoryForge 前端 Demo，提供小说导入、故事分析、模拟生成、剧本编辑与 YAML 导出完整演示流程。

## 实现思路

- 使用 Vue 3、TypeScript 与 Vite 构建单页应用。
- 使用本地模拟数据保证无需 API Key 即可稳定复现。
- 使用浏览器 LocalStorage 自动保存项目。
- 使用 js-yaml 将结构化剧本实时转换为 YAML。

## 测试方式

1. 运行 \`npm install\`。
2. 运行 \`npm run build\`，确认类型检查和生产构建通过。
3. 运行 \`npm run dev\`，点击“体验示例”走通完整流程。

## 来源说明

本 PR 未复用过往项目代码；第三方依赖及其用途已在 README 中列明。`

  return github('/pulls', {
    method: 'POST',
    body: JSON.stringify({
      title: config.prTitle,
      head: config.branch,
      base: config.baseBranch,
      body,
    }),
  })
}

async function main() {
  console.log(`正在检查 ${config.owner}/${config.repo}…`)
  const repository = await getRepository()
  const baseSha = await ensureBaseBranch(repository)
  const parentSha = await ensureFeatureBranch(baseSha)

  const files = await collectFiles(config.root)
  console.log(`正在上传 ${files.length} 个文件到 ${config.branch}…`)
  const tree = []
  for (const [index, file] of files.entries()) {
    tree.push(await createBlob(file))
    console.log(`[${index + 1}/${files.length}] ${relative(config.root, file)}`)
  }

  const commit = await createCommit(parentSha, tree)
  await updateBranch(commit.sha)
  console.log(`提交已推送：${commit.html_url}`)

  if (config.createPullRequest) {
    const pullRequest = await createPullRequest()
    console.log(`PR 已准备好：${pullRequest.html_url}`)
  } else {
    console.log('已跳过创建 PR。')
  }
}

function validateConfig() {
  const missing = Object.entries({
    GITHUB_OWNER: config.owner,
    GITHUB_REPO: config.repo,
    GITHUB_TOKEN: config.token,
  })
    .filter(([, value]) => !value)
    .map(([key]) => key)

  if (missing.length) {
    console.error(`缺少环境变量：${missing.join(', ')}`)
    console.error('请参考 README 中的“通过 GitHub API 推送”章节。')
    process.exit(1)
  }

  if (config.branch === config.baseBranch) {
    console.error('GITHUB_BRANCH 必须是功能分支，不能与 GITHUB_BASE_BRANCH 相同。')
    process.exit(1)
  }
}

main().catch((error) => {
  console.error(error.message)
  process.exit(1)
})
