# 白砾电子

## 当前结构

- `frontend/`：用户提供的新版单文件 UI，以及 API 对接脚本。
- `backend/server.py`：同源静态服务、选题评估 API、功能方案 API。
- `backend/activity_store.py`：测试活动记录、后台查询与状态处理的本地持久化。
- `backend/ai_client.py`：OpenAI 兼容接口客户端，Key 仅由后端读取。
- `backend/import_projects.py`：将总表导入后端私有 JSON 内容库。
- `backend/prompt_template.txt`：待用户补充的正式功能方案提示词。
- `data/projects.json`：从 `D:\Working Repository\总表.xlsx` 导出的私有内容库，不能放到公开静态目录。
- 根目录原有 `index.html`、`styles.css`、`soft-ui.css`、`app.js`：上一版纯静态原型，仅保留备查，不是当前后端入口。

## 本地启动

```powershell
python backend\server.py
```

默认访问地址：`http://127.0.0.1:43210/`。

管理后台地址：`http://127.0.0.1:43210/admin`。需要先在 `.env` 配置：

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=请设置强密码
ADMIN_SESSION_SECONDS=28800
ADMIN_SECURE_COOKIE=false
```

公网 HTTPS 部署时将 `ADMIN_SECURE_COOKIE` 设为 `true`。后台使用服务端会话和 `HttpOnly` Cookie，不在前端保存管理员密码或登录令牌。

## 配置 AI

复制 `.env.example` 为 `.env`，填写 DeepSeek API Key：

```env
AI_API_KEY=你的DeepSeek_Key
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-v4-flash
AI_TIMEOUT_SECONDS=60
AI_JSON_MODE=true
AI_THINKING=disabled
COMPONENT_DESCRIPTION_MODE=fixed
```

`.env` 已加入 `.gitignore`，不得提交或放到前端目录。配置后需要重启后端。

AI 启用后，题目评分和功能方案会使用“大模型 + 相似项目摘要 + prd-gen 规则”生成；结果仍会经过数量限制、器件规则和字段校验。AI 未配置或调用失败时会明确回退到规则引擎。

`COMPONENT_DESCRIPTION_MODE` 是预留给未来商家端的服务端配置，不在当前用户端展示。`fixed` 使用本地元器件说明库中的固定句，`ai` 让模型结合题目逐器件生成一句说明。

可通过环境变量调整监听地址和端口：

```powershell
$env:MCU_HOST='0.0.0.0'
$env:MCU_PORT='43210'
python backend\server.py
```

服务器公网部署时，应在前方配置 HTTPS 反向代理，不建议直接暴露 Python 服务端口。

## 更新内容库

默认从 `D:\Working Repository\总表.xlsx` 导入：

```powershell
python backend\import_projects.py
```

使用其他路径：

```powershell
$env:MCU_SOURCE_XLSX='D:\path\总表.xlsx'
python backend\import_projects.py
```

导入脚本需要 `openpyxl`；后端运行时只读取已导出的 JSON，不依赖 `openpyxl`。

## 已实现接口

- `GET /api/health`
- `POST /api/topics/evaluate`
- `POST /api/components/recommend`
- `GET /api/components/catalog?topic=...`
- `POST /api/designs/generate`
- `POST /api/events/pdf-export`
- `POST /api/admin/login`
- `GET /api/admin/overview`
- `GET /api/admin/topics`
- `GET /api/admin/components`
- `GET /api/admin/feedback`
- `GET /api/admin/errors`
- `GET /api/admin/export?dataset=topics|components|feedback|errors`

`/api/designs/generate` 接收配置页提交的 `counts`、`components` 和 `requirements`。后端会锁定用户选择的器件与数量；额外按键不计入传感器数量。`必须使用`可指定主控或已选器件，`不能使用`与当前选型冲突时返回可直接展示的错误信息。

`/api/components/recommend` 会先接收 AI 候选，再按 PID 电机、温室、门禁、消防和物联网等题目领域的器件白名单过滤无关项，并从领域标准池补足默认的 `1 个显示器 / 3 个传感器 + 1 个按键 / 2 个执行驱动器`。

元器件索引通过 `python backend/import_components.py` 导入到 `data/component_catalog.json`。完整目录仅供后端使用，并保留后续资料打包所需的库文件夹、文件名和资料链接；目录接口只向前端返回当前题目相关的约 20 个标签，不返回本地路径。

截图 OCR 尚未接入。前端会明确提示用户先输入文字，不会用演示数据伪装识别结果。

测试活动数据写入服务端私有的 `data/activity_store.json`，该文件已加入 `.gitignore`。当前用户侧反馈入口按测试计划暂不启用，因此后台“用户反馈”页会显示真实空状态。PDF 仍由浏览器 `window.print()` 导出，后台统计的是“打开 PDF 导出流程”，浏览器无法确认用户是否最终保存文件。
