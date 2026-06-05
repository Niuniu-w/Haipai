# StoryForge 后端

当前后端提供 FastAPI 健康检查和 SQLite 项目持久化接口。
开发环境 CORS 允许 `127.0.0.1` 和 `localhost` 的本地前端端口访问。

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
PUT    /api/projects/{id}  更新项目
DELETE /api/projects/{id}  删除项目
POST   /api/projects/{id}/parse-chapters  识别并保存项目章节
POST   /api/projects/{id}/analyze         分析并保存故事信息
POST   /api/projects/{id}/generate        生成并保存结构化剧本场景
GET    /api/projects/{id}/generation-status  查询剧本生成状态
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
STORYFORGE_LLM_BASE_URL=https://api.openai.com/v1
STORYFORGE_LLM_MODEL=gpt-5-mini
```

重新启动后端后，`POST /api/projects/{id}/analyze` 会优先使用 OpenAI Responses API，并通过 JSON Schema 和 Pydantic 校验结构化结果。未配置密钥、模型请求失败或结果校验失败时，会自动回退本地规则分析。

同一模型配置也用于 `POST /api/projects/{id}/generate`。接口会根据章节、故事概要、人物和改编设置生成结构化场景，并将结果保存到 SQLite；未配置密钥或调用失败时自动使用后端本地规则生成。

`backend/.env` 已加入 `.gitignore`，不得提交 API Key。

## 测试

```bash
backend/.venv/bin/python -m pytest backend/tests
```
