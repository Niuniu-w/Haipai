# 织幕 StoryForge

> 让故事从纸上走进镜头。

织幕 StoryForge 是一款面向小说作者、编剧与内容创作团队的 AI 小说转剧本工具。用户只需导入小说，系统即可完成章节识别、故事分析、逐章剧本生成、可视化编辑与 YAML 导出，将漫长的改编过程转化为清晰、可控、可继续创作的工作流。

项目重点解决小说改编中的三个核心问题：

- **长文本难以一次处理**：采用逐章生成机制，真实展示进度，并支持单章重新生成。
- **小说语言难以直接拍摄**：减少旁白，通过人物对白、对应动作和场景调度推动剧情。
- **AI 结果难以继续编辑**：将剧本转换为结构化数据，提供可视化工作台与实时 YAML 预览。

## 核心亮点

### 1. 从小说到剧本的完整创作闭环

系统覆盖小说改编的完整流程，而不是只生成一段文本：

```text
导入小说
  → 自动识别章节
  → 分析故事与人物
  → 设置改编方向
  → 逐章生成剧本
  → 编辑场景、动作与对白
  → 校验并导出 YAML
```

用户可以在每个阶段查看、调整和确认结果，让 AI 成为可协作的创作助手。

### 2. 面向长篇故事的逐章生成

后端将剧本生成拆分到每个章节执行，每章完成后立即保存结果与状态。生成页面展示真实章节进度，失败章节可以单独重试，已完成章节无需重复生成。

这种方式降低了长文本对模型上下文的压力，也让用户能够针对特定章节持续打磨。

### 3. 对白驱动的结构化剧本

生成策略默认减少小说式旁白，优先通过人物对白呈现信息、冲突与选择。场景内容按照实际演出顺序混排动作与对白，每条对白同时记录：

- 说话人物
- 对白内容
- 人物情绪
- 对应动作

最终结果更接近可以继续创作和排演的剧本初稿，而不是简单的小说摘要。

### 4. AI 分析与人工编辑协同

系统会提取并展示：

- 整体故事概要、题材、时代与风格
- 主要人物、人物简介与人物关系
- 每章概要与关键事件
- 场景时间、地点、氛围与出场人物

分析结果和生成结果均可继续编辑。人物改名会同步相关引用，场景可调整所属章节，动作与对白可自由增删和排序。

### 5. 可视化剧本工作台

工作台采用三栏布局：

- **左侧**：章节与场景目录
- **中间**：结构化场景编辑器
- **右侧**：实时 YAML 预览与原文对照

用户可以添加或删除场景、维护出场人物、调整动作和对白顺序，并对单个场景发出 AI 润色指令，例如“让冲突更强烈”“增加对白”或“改成夜晚”。

### 6. 稳定、可复用的结构化输出

剧本使用版本化的 `storyforge-script/v2` 数据结构，并通过 JSON Schema、Pydantic 与 YAML 序列化保证前后端数据一致。导出的 YAML 可用于后续创作、内容管理、自动排版或其他 AI 工作流。

## 主要功能

| 核心模块 | 功能效果 |
| --- | --- |
| 小说导入 | 支持粘贴文本以及上传 `.txt`、`.md`、`.docx` 文件，兼容常见中文文本编码 |
| 章节识别 | 自动识别“第一章”“第1章”“Chapter 1”等标题，并支持手动拆分、合并和修改 |
| 故事分析 | 提取概要、题材、时代、风格、人物、关系、章节摘要与关键事件 |
| 改编设置 | 支持改编模式、目标剧本类型、对白密度和目标场景数量 |
| 逐章生成 | 按章节生成结构化场景，展示真实进度，支持单章重新生成与失败重试 |
| 剧本编辑 | 编辑场景信息、出场人物、动作、对白、情绪、章节归属与来源摘要 |
| 场景润色 | 使用自然语言指令针对单个场景进行调整与优化 |
| 项目管理 | 自动保存项目，支持历史项目打开、继续编辑和删除 |
| 剧本导出 | 实时预览、复制并下载 UTF-8 YAML 剧本文件 |

## 关键实现

### AI 结构化生成

项目接入阿里云 DashScope `qwen-plus`，通过 OpenAI 兼容接口调用模型。模型输出首先被约束为结构化 JSON，再由 Pydantic 校验并转换为前端可编辑的数据和 YAML 文件。

```text
小说章节
  → 大模型分析与改编
  → 结构化 JSON
  → Pydantic 数据校验
  → SQLite 持久化
  → 可视化编辑
  → YAML 导出
```

当模型服务暂时不可用时，系统可使用本地分析与生成规则继续完成演示流程，保证作品体验稳定。

### 生成状态与单章重试

每个章节拥有独立的生成状态、尝试次数、生成方式和场景数量。前端按章节调用后端接口，后端完成一章后立即保存，因此用户可以清楚了解当前进度，并只重新处理需要修改的章节。

### 数据保存与一致性

- 使用 SQLite 与 SQLAlchemy 保存项目、章节、人物和剧本场景。
- 使用版本号与 `If-Match` 乐观锁避免并发保存覆盖。
- 使用串行自动保存保证编辑结果按正确顺序写入。
- 浏览器 LocalStorage 提供本地保存能力。
- 章节源内容变化后，自动刷新相关分析与生成状态。

### 剧本 Schema

每个场景包含来源章节、标题、地点、时间、氛围、出场人物、来源摘要和按演出顺序排列的内容。动作与对白使用统一 `content` 列表，便于编辑、排序和后续程序处理。

```yaml
schema_version: storyforge-script/v2
scenes:
  - id: SC-01
    source_chapter: 第一章 雨夜来信
    location: 咖啡馆
    time: 夜
    characters:
      - 林墨
    content:
      - type: action
        action: 林墨推开咖啡馆的门。
      - type: dialogue
        action: 林墨停下脚步，警惕地环顾四周。
        character: 林墨
        emotion: 疑惑
        line: 是谁留下的？
```

## 系统架构

```text
Vue 3 + TypeScript 前端
  ├── 小说导入与章节编辑
  ├── 故事分析与改编设置
  ├── 逐章生成进度
  └── 剧本编辑与 YAML 预览
              │
              │ REST API
              ▼
FastAPI 后端
  ├── 章节解析服务
  ├── 大模型分析与生成服务
  ├── 单场景润色服务
  ├── 项目保存与版本控制
  └── YAML 校验与导出服务
              │
              ├── DashScope qwen-plus
              └── SQLite
```

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite |
| 后端 | FastAPI、Pydantic、SQLAlchemy、Uvicorn |
| 数据库 | SQLite |
| 大模型 | DashScope `qwen-plus`、OpenAI 兼容接口、HTTPX |
| 文件与导出 | Mammoth、js-yaml、PyYAML |
| 测试 | Pytest、Vue TypeScript 类型检查、Vite Production Build |

## 工程质量

- 后端核心业务拥有 `36` 项自动化测试，覆盖项目管理、章节识别、故事分析、逐章生成、单章重试、场景润色和 YAML 导出。
- 前端通过 Vue TypeScript 类型检查与 Vite Production Build 验证。
- FastAPI 自动生成交互式接口文档，便于评委查看和调用项目 API。
- 前后端围绕统一的项目、章节、人物、场景和剧本内容数据结构协作。

## 评委快速体验

环境要求：Node.js 20+、Python 3.11+。

### 1. 启动后端

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn app.main:app --reload --app-dir backend
```

后端地址：`http://127.0.0.1:8000`  
接口文档：`http://127.0.0.1:8000/docs`

### 2. 启动前端

```bash
npm install
npm run dev
```

打开终端显示的本地前端地址，点击首页的“体验示例”即可快速体验完整流程。

### 3. 配置真实大模型

复制后端配置示例并填写 DashScope API Key：

```bash
cp backend/.env.example backend/.env
```

```dotenv
STORYFORGE_LLM_API_KEY=你的_API_Key
STORYFORGE_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
STORYFORGE_LLM_MODEL=qwen-plus
STORYFORGE_LLM_PROVIDER=dashscope-chat-completions
STORYFORGE_LLM_API_STYLE=chat-completions
```


## 项目目录

```text
Haipai/
├── src/
│   ├── api/             前端 API 客户端
│   └── components/      导入、分析、生成和编辑页面
├── backend/
│   ├── app/             FastAPI 服务、AI 服务与数据模型
│   └── tests/           后端自动测试
├── docs/                项目规划与说明
└── package.json         前端依赖与运行命令
```

## 项目愿景

织幕希望连接小说创作与影视表达：保留原著的故事核心，同时让创作者能够更快地看见人物如何开口、场景如何发生、文字如何走进镜头。

## 视频demo

https://www.bilibili.com/video/BV1CuEh6GEve/
