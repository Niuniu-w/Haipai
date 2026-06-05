# 织幕 StoryForge

织幕是一款面向小说作者的 AI 辅助剧本创作 Demo。用户可以导入小说文本，确认章节结构，查看故事分析结果，逐章生成剧本，并在三栏工作台中编辑和导出 YAML。

> 当前版本为无需 API Key 的前端演示原型。AI 分析和生成使用内置模拟数据，便于评审稳定复现完整流程。

## Demo 视频

待上传后补充可公开访问的 Bilibili 或云盘链接。

## 核心功能

- 粘贴或上传 `.txt` / `.md` 小说，自动识别常见章节标题
- 内置四章示例小说，一键体验完整改编流程
- 展示故事概要、主要人物、人物关系和章节关键事件
- 设置改编模式与目标剧本类型
- 模拟逐章生成进度和结构校验
- 三栏剧本工作台，编辑场景、动作和对白
- 实时生成、复制并下载 YAML
- 模拟 AI 单场景润色
- 使用浏览器本地存储自动保存项目

## 原创功能说明

本项目的产品流程、界面设计、示例小说、章节解析逻辑、模拟分析数据、剧本工作台交互和 YAML 数据转换均针对本项目独立实现。

第三方框架和组件仅用于基础工程能力、图标与 YAML 序列化，详见“第三方依赖”。

## 演示流程

1. 进入首页，点击“体验示例”。
2. 在导入页检查原文与自动识别的四个章节。
3. 进入分析页，查看并编辑故事概要、人物与改编设置。
4. 启动剧本生成，等待四章生成完成。
5. 进入工作台，编辑场景信息、动作或对白。
6. 检查右侧实时 YAML，复制或下载剧本文件。

## 技术栈

- Vue 3
- TypeScript
- Vite
- CSS
- Browser LocalStorage

## 第三方依赖

| 依赖 | 用途 |
| --- | --- |
| `vue` | 前端界面与响应式状态 |
| `vite` | 本地开发与生产构建 |
| `typescript` / `vue-tsc` | 类型检查 |
| `js-yaml` | 将结构化剧本转换为 YAML |
| `lucide-vue-next` | 界面图标 |
| `@vitejs/plugin-vue` | Vite 的 Vue 单文件组件支持 |

## 本地运行

环境要求：Node.js 20 或更高版本。

```bash
npm install
npm run dev
```

浏览器访问 `http://127.0.0.1:4173/`。

## 测试与构建

运行生产构建，同时执行 Vue 与 TypeScript 类型检查：

```bash
npm run build
```

构建产物生成在 `dist/`，该目录不提交至代码仓库。

## 通过 GitHub API 推送

项目提供不依赖 Git 或 GitHub CLI 的推送脚本。它会：

- 将当前项目文件推送到一个功能分支
- 排除 `.git`、`node_modules` 和 `dist` 等目录
- 创建一个包含功能描述、实现思路和测试方式的 PR
- 仅从环境变量读取 Token，不会将 Token 写入仓库

Token 需要拥有目标仓库的 `Contents: Read and write` 与 `Pull requests: Read and write` 权限。
如果目标仓库完全为空，脚本会先创建一个最小的 `main` 初始化提交，再通过功能分支提交完整项目。

在终端中运行：

```bash
read -s GITHUB_TOKEN
export GITHUB_TOKEN
export GITHUB_OWNER="Niuniu-w"
export GITHUB_REPO="Haipai"
export GITHUB_BASE_BRANCH="main"
export GITHUB_BRANCH="feat/initial-storyforge-demo"
npm run github:push
unset GITHUB_TOKEN
```

使用 `read -s` 输入 Token 时，终端不会显示输入内容，也不会将 Token 写入 shell 历史。

## 项目结构

```text
src/
  components/        # 导入、分析、生成和剧本工作台页面
  App.vue            # 应用入口与流程状态
  data.ts            # 内置演示小说及模拟数据
  types.ts           # 核心数据类型
  utils.ts           # 章节识别、场景生成和 YAML 导出
  styles.css         # 全局视觉与页面布局
PROJECT_PLAN.md      # 项目计划与完整产品设计
```

## 当前限制与后续计划

- 当前 AI 分析和生成采用本地模拟数据，尚未连接模型 API。
- 当前项目仅保存在浏览器本地，尚未实现账户和云端同步。
- 后续将按照 `PROJECT_PLAN.md` 接入 FastAPI、SQLite 和大模型服务。

## 开源与引用说明

本项目未复用作者过往项目代码。若后续引入其他来源的代码或素材，将在对应 PR 描述和本节中注明来源。
