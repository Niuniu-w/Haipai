# StoryForge 后端

当前后端提供 FastAPI 健康检查和 SQLite 项目持久化接口。
开发环境 CORS 默认允许 `127.0.0.1` 和 `localhost` 的本地前端端口访问；线上域名可通过环境变量配置。

## 安装

在项目根目录执行：

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
```

## 启动

```bash
backend/.venv/bin/uvicorn app.main:app --reload --app-dir backend
```

启动后可以访问：

- 健康检查：`http://127.0.0.1:8000/api/health`
- API 文档：`http://127.0.0.1:8000/docs`
- 项目列表：`http://127.0.0.1:8000/api/projects`
- AI 配置状态：`http://127.0.0.1:8000/api/ai/status`

## 项目接口

```text
POST   /api/projects       创建项目
GET    /api/projects       获取项目列表
GET    /api/projects/{id}  获取项目详情
PUT    /api/projects/{id}  更新项目（必须携带 If-Match 项目版本号）
DELETE /api/projects/{id}  删除项目
POST   /api/projects/{id}/parse-chapters  识别并保存项目章节
POST   /api/projects/{id}/analyze         分析并保存故事信息
POST   /api/projects/{id}/generate        生成并保存结构化剧本场景
POST   /api/projects/{id}/generation/start  初始化逐章生成任务
POST   /api/projects/{id}/chapters/{chapter_id}/generate  生成或重新生成单章
GET    /api/projects/{id}/generation-status  查询剧本生成状态
GET    /api/projects/{id}/validate-script    校验剧本导出结构
GET    /api/projects/{id}/export/yaml        校验并导出 YAML
GET    /api/projects/script-schema           获取版本化剧本 JSON Schema
POST   /api/projects/{id}/scenes/{scene_id}/polish  润色并保存单个场景
```

项目默认保存在 `backend/storyforge.db`。这是本地运行数据，已加入 `.gitignore`。

章节解析接口接收 `raw_text`，识别中文“第一章”和英文“Chapter 1”等标题，生成基础摘要与关键事件，并返回是否满足至少 3 章的校验结果。

故事分析接口会根据后端配置优先使用真实大模型，并保存分析模式、状态、错误和尝试次数；未配置密钥或模型调用失败时使用可离线运行的本地规则。

## 配置真实大模型

复制配置示例并填写 API Key：

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

重新启动后端后，`POST /api/projects/{id}/analyze` 会优先使用配置的真实模型。DashScope 的 `qwen-plus` 通过 OpenAI 兼容的 Chat Completions JSON Mode 返回结构化结果，再由 Pydantic 执行严格校验。未配置密钥、模型请求失败或结果校验失败时，会自动回退本地规则分析。

后端同时保留 OpenAI Responses API 兼容能力。接入支持 Responses JSON Schema 的服务时，将 `STORYFORGE_LLM_API_STYLE` 设置为 `responses`，并配置对应的 Base URL、模型与提供商名称。

同一模型配置也用于剧本生成。前端先初始化逐章任务，再按章节逐个调用生成接口；每章完成后会立即保存场景和章节状态到 SQLite。失败章节与已完成章节都可以单独重新生成，不会重新调用其他章节。未配置密钥或模型调用失败时自动使用后端本地规则生成。

项目中的 `dialogueDensity` 和 `targetSceneCount` 会参与生成：目标总场景数按章节分配且每章至少一场；对白密度会传入模型提示，并控制本地规则提取对白的上限。

通用项目更新接口使用 `revision` 乐观锁。客户端从项目响应读取 `data.revision`，更新时通过 `If-Match` 请求头传回；版本过期返回 `409`，缺少版本号返回 `428`。

YAML 导出使用 `storyforge-script/v1` 正式 Pydantic/JSON Schema，并校验作品标题、唯一章节与场景编号、每章至少一个场景、来源章节、动作描述、人物关系、出场人物和对白人物关系。结构无效时返回 `422` 和具体错误列表，校验通过后才返回 UTF-8 YAML 文件。

单场景润色接口在已配置模型时调用对应的真实模型接口；未配置或调用失败时使用后端本地规则，并持久化润色后的场景。

## 部署与安全配置

```dotenv
# 线上前端域名，多个域名以逗号分隔
STORYFORGE_CORS_ORIGINS=https://example.com,https://admin.example.com

# 可选；设置后除健康检查外的 /api 路由都需要 Bearer Token
STORYFORGE_API_TOKEN=请使用高强度随机值
```

前端需设置相同的 `VITE_API_TOKEN`。这提供基础 API 保护，但不等同于账户、角色权限或多人协作体系。

数据库启动时会运行并记录 `backend/app/migrations.py` 中的版本化迁移。新增数据库结构时应追加新版本，不修改已经应用的迁移。

`backend/.env` 已加入 `.gitignore`，不得提交 API Key。

## 测试

```bash
backend/.venv/bin/python -m pytest backend/tests
```
