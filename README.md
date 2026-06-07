# 织幕 StoryForge

织幕是一款面向小说作者的 AI 辅助剧本创作工具。它将小说改编过程拆分为章节识别、故事分析、剧本生成和编辑导出四个步骤，帮助创作者快速得到可继续修改的结构化剧本初稿。

当前仓库提供可完整体验的前端 Demo 和可选 FastAPI 后端。无需配置 API Key；启动后端后，项目会自动保存到本地 SQLite 数据库。

## 项目亮点

- 自动识别小说中的常见章节标题
- 提取并展示故事概要、人物关系和章节关键事件
- 支持忠于原著、影视化增强、短剧快节奏等改编模式
- 对白密度和目标场景数会同时影响真实模型提示与本地规则生成
- 后端逐章生成并立即保存结构化剧本，支持失败重试和单章重新生成
- 在三栏工作台中编辑人物关系、章节分析、场景归属、出场人物、动作和对白顺序
- 使用版本化正式 Schema 校验、预览、复制并下载 YAML 剧本
- 支持 LocalStorage 与 SQLite 双重自动保存、串行保存和版本冲突检测
- 支持打开、确认删除和滚动查看全部后端历史项目
- 支持单场景真实模型润色，并在未配置或失败时回退本地规则

## 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 小说导入与章节识别 | 已完成 | 支持粘贴文本、上传 `.txt` / `.md` / `.docx`，由后端识别并保存章节；章节源内容变化后会清除旧分析和旧剧本 |
| 小说分析 | 已完成 | 可使用真实大模型或本地规则生成概要、题材、人物和关系，结果可编辑并保存 |
| 剧本生成 | 已完成 | 后端逐章调用模型并立即保存，目标场景数按章节分配，对白密度参与生成，支持失败重试和单章重新生成 |
| 剧本编辑工作台 | 已完成 | 支持人物及引用同步、关系与章节分析编辑、章节划分、场景归属、动作和对白排序 |
| YAML 导出 | 已完成 | 使用 `storyforge-script/v1` 正式 Schema，支持前后端校验、服务端导出、复制和下载 |
| 项目自动保存 | 已完成 | 串行保存并使用项目版本号检测冲突；离线新内容不会被旧远端数据无条件覆盖 |
| 历史项目管理 | 已完成 | 首页支持打开、确认删除和查看全部后端历史项目 |
| 大模型故事分析 | 已完成可选接入 | 默认支持 DashScope `qwen-plus`，并兼容 Responses API；未配置或失败时自动回退本地规则 |
| FastAPI 后端骨架 | 已完成 | 提供健康检查、可配置 CORS、可选 API Token、版本迁移和自动测试 |
| 前后端健康检查连接 | 已完成 | 前端显示后端连接状态并支持自动重试 |
| SQLite 数据库 | 已完成 | 使用 SQLAlchemy 提供项目创建、查询、更新和删除接口 |
| 后端章节解析 | 已完成 | 支持中英文章节标题、基础摘要、关键事件和至少 3 章校验 |
| 后端故事分析 | 已完成 | 支持真实模型结构化分析、本地回退、状态和尝试次数保存 |
| 后端剧本生成 | 已完成 | 支持场景结构化生成、SQLite 保存、生成状态和失败回退 |

## 快速体验

环境要求：Node.js 20 或更高版本。

```bash
npm install
npm run dev
```

访问 `http://127.0.0.1:4173/`，点击首页的“体验示例”，即可走通完整改编流程。

生产构建与类型检查：

```bash
npm run build
```

后端启动：

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn app.main:app --reload --app-dir backend
```

访问 `http://127.0.0.1:8000/api/health` 检查后端状态，访问 `http://127.0.0.1:8000/docs` 查看 API 文档。数据库默认保存在 `backend/storyforge.db`，该运行数据不会提交到仓库。详细说明见 [`backend/README.md`](./backend/README.md)。

前端默认连接 `http://127.0.0.1:8000`。部署或更换后端地址时，复制 [`.env.example`](./.env.example) 为 `.env`，并设置 `VITE_API_BASE_URL`。

如后端设置了 `STORYFORGE_API_TOKEN`，前端需要将同一个值配置为 `VITE_API_TOKEN`。线上前端域名需加入后端 `STORYFORGE_CORS_ORIGINS`，多个域名使用逗号分隔。

真实大模型为可选配置。后端默认配置示例使用阿里云 DashScope OpenAI 兼容接口与 `qwen-plus`；参考 [`backend/.env.example`](./backend/.env.example) 设置密钥。密钥只由后端读取，未配置时项目仍使用本地规则完成故事分析。

## 演示流程

1. 导入小说或载入内置示例。
2. 确认自动识别的章节结构。
3. 查看故事概要、人物关系和章节事件。
4. 设置改编模式并启动剧本生成。
5. 在工作台中编辑场景、动作和对白。
6. 预览并导出 YAML 剧本。

## 技术栈

- Vue 3、TypeScript、Vite
- FastAPI、SQLAlchemy、SQLite、Uvicorn、Pytest
- `js-yaml`：结构化剧本 YAML 序列化
- `mammoth`：浏览器端提取 DOCX 正文
- `lucide-vue-next`：界面图标
- Browser LocalStorage：后端不可用时的本地保存兜底

## 目录结构

```text
Haipai/
├── src/                 Vue 前端源码
│   ├── api/             后端 API 客户端
│   └── components/      流程页面与编辑工作台
├── backend/
│   ├── app/             FastAPI、业务服务与数据模型
│   └── tests/           后端自动测试
├── docs/                项目规划与开发文档
└── package.json         前端依赖与运行命令
```

详细文档索引见 [`docs/README.md`](./docs/README.md)。

## 原创说明

本项目的产品流程、界面设计、示例小说、章节解析逻辑、模拟分析数据、剧本工作台交互和 YAML 数据转换均针对本项目独立实现。第三方框架和依赖仅用于基础工程能力、图标、DOCX 正文提取和 YAML 序列化。

当前仍是单用户原型，不包含账户体系、细粒度权限、实时协作、云数据库托管、线上环境和公开 Demo 视频。文件导入仅支持 `.txt`、`.md`、`.docx`，不支持旧版 `.doc`、PDF、EPUB 和扫描件 OCR。

## Demo 视频

待补充公开可访问的视频链接。
