# Mini Scheduler

一个基于 FastAPI 的轻量任务调度与执行系统，支持 Cron 定时、手动触发、批量操作、执行记录、重试与基础的 JWT 身份认证，同时提供简单易用的网页界面与 API。

#获取方式
从https://github.com/ZMJJKK123-hub/mini-schedulerclone即可

## 功能特性
- 定时任务：使用 cron 表达式控制执行时间，5 秒轮询，支持 `PENDING/ACTIVE/RUNNING/FAILED` 状态流转。
- 手动触发：支持单任务或批量设置 `force_run_at` 立即触发执行。
- 批量操作：批量删除、批量暂停、批量强制运行。
- 执行记录：保存 `stdout/stderr/error`，可查看单次执行详情。
- 运行超时恢复：`RUNNING` 超过 1 分钟自动标记为 `FAILED`。
- 重试机制：失败后按 `retry_count/max_retries` 进行重试并回到 `PENDING`。
- 认证与会话：JWT Bearer + Cookie（浏览器自动跳转登录页）。
- 网页界面：任务列表、创建/编辑、详情页、执行详情页、登录/注册页。
- 日志与轮转：`logs/scheduler.log` 文件轮转 + 控制台输出。

## 目录结构

```
mini-scheduler/
   api/                # FastAPI 路由与页面
      main.py           # 应用入口、认证中间件、UI 与 API 路由
   common/             # 通用层
      db.py             # SQLite 连接、表结构、数据操作
      models.py         # 数据模型（Task）
      utils.py          # 工具函数（cron 下次运行时间）
      auth.py           # 认证逻辑（JWT、用户增删查）
   scheduler/
      scheduler.py      # 调度器主循环与执行器
   templates/          # Jinja2 模板（UI 页面）
   worker/
      worker.py         # 预留（当前为空）
   add_column.py       # 给 tasks 增加 `last_error` 字段的脚本
   reset_db.py         # 清库并重置自增 ID 的脚本
   fake_data.py        # 制造僵尸 RUNNING 任务用于演示
   requirements.txt    # 依赖列表
   config.py           # 日志配置（文件轮转 + 控制台）
   data/               # SQLite 数据文件目录（data/scheduler.db）
   logs/               # 日志输出目录
```

## 依赖与环境

`requirements.txt`：

```
fastapi
uvicorn
redis
croniter
jinja2
python-multipart
PyJWT
```

可选环境变量：
- `SECRET_KEY`：JWT 签名密钥（默认：`your-secret-key-change-in-production-12345678`，生产环境务必更改）。

## 快速开始（Windows）

1) 创建并激活虚拟环境，安装依赖：

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r mini-scheduler/requirements.txt
```

2) 初始化数据库并启动服务：

```powershell
cd mini-scheduler
python reset_db.py   # 可选：清空并初始化数据库
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

3) 打开浏览器访问：
- UI 页：`http://127.0.0.1:8000/ui/tasks`
- 登录页：`http://127.0.0.1:8000/login`
- 注册页：`http://127.0.0.1:8000/register`
- 文档：`http://127.0.0.1:8000/docs`

首次启动会自动创建默认管理员用户：
- 用户名：`admin`
- 密码：`admin123`

提示：登录后浏览器会在 Cookie 中保存 `access_token`，用于继续访问受保护页面。

## 架构与工作流

- 应用入口在 [api/main.py](mini-scheduler/api/main.py)：
   - 启动事件 `startup()`：调用 `init_db()` 初始化表结构，并启动后台调度线程 `run_scheduler()`。
   - 中间件：除少数公开路径外，所有请求需要携带 Bearer Token 或 Cookie 中的 `access_token`。
   - UI 路由：任务列表、创建、详情、编辑、执行详情等 Jinja2 模板页面。
   - API 路由：任务创建/查询、批量操作、执行详情、Cron 预览等。

- 数据层在 [common/db.py](mini-scheduler/common/db.py)：
   - SQLite 文件位于 `data/scheduler.db`。
   - 表：`tasks`、`executions`、`users`；启动时自动建表与字段补齐（如 `force_run_at`、`retry_count`、`max_retries`）。
   - 默认创建 `admin` 用户（密码明文，仅示例用途）。

- 模型在 [common/models.py](mini-scheduler/common/models.py)：
   - `Task`：含 `status/last_run_at/force_run_at/retry_count/max_retries/last_error` 等字段。

- 调度与执行在 [scheduler/scheduler.py](mini-scheduler/scheduler/scheduler.py)：
   - 每 5 秒扫描任务，根据 `cron` 或 `force_run_at` 判断执行时机。
   - 通过 `try_mark_running()` 抢占执行，避免并发重复运行。
   - 子线程执行命令（`subprocess.run(shell=True)`），记录执行日志与结果状态。
   - 超时恢复：`RUNNING_TIMEOUT = 1 分钟`，超过自动标记为 `FAILED`。
   - 失败重试：比较 `retry_count/max_retries`，未达上限则回到 `PENDING`。

- 认证在 [common/auth.py](mini-scheduler/common/auth.py)：
   - `create_access_token()` 生成 JWT，`verify_token()` 验证。
   - `create_user()` 与 `authenticate_user()` 走数据库逻辑。
   - 依赖 `get_current_user_from_bearer()` 支持 Header/Cookie 两种令牌来源。

- 工具在 [common/utils.py](mini-scheduler/common/utils.py)：
   - `next_run_times()` 提供 Cron 表达式预览接口使用。

- 日志在 [config.py](mini-scheduler/config.py)：
   - `logs/scheduler.log` 自动轮转，控制台与文件双通道输出。

## UI 路由
- `GET /ui/tasks`：任务列表，支持搜索（`q`）与状态筛选（`status`），分页（`page`）。
- `GET /ui/tasks/create`：创建任务表单。
- `POST /ui/tasks/create`：提交创建任务。
- `GET /ui/tasks/{task_id}`：任务详情与近 20 条执行记录。
- `GET /ui/tasks/{task_id}/edit`：编辑任务表单。
- `POST /ui/tasks/{task_id}/update`：更新任务。
- `GET /ui/executions/{execution_id}`：执行详情页面。
- `GET /login` / `GET /register`：登录/注册页面。

## API 速览

认证相关：
- `POST /auth/login`（Form: `username`, `password`）→ 返回 JSON 含 `access_token`，并设置 HttpOnly Cookie。
- `POST /auth/register`（Form: `username`, `password`, `confirm`）→ 303 重定向登录页。
- `GET /auth/me`（Bearer/Cookie）→ 当前用户信息。
- `GET /auth/logout` → 清除 Cookie 并跳转登录。

任务相关：
- `POST /tasks`（JSON: `name`, `cron`, `command`）→ 创建任务。
- `GET /tasks` → 返回任务列表（JSON）。
- `POST /tasks/{task_id}/run` → 手动触发任务执行（设置 `force_run_at`）。
- `POST /tasks/{task_id}/toggle` → 切换 `ACTIVE/PAUSED`。
- `POST /tasks/{task_id}/cleanup?keep_last=50` → 清理旧执行记录，仅保留最近 `keep_last` 条。

批量相关（支持 Form 或 JSON 数组 `task_ids`）：
- `POST /tasks/bulk/delete`
- `POST /tasks/bulk/pause`
- `POST /tasks/bulk/force_run`

执行记录：
- `GET /executions/{execution_id}` → 执行详情（JSON）。
- `GET /api/executions/{execution_id}` → 与上同（用于 API 命名空间）。

Cron 预览：
- `GET /api/cron/next?cron=CRON&n=5` → 返回未来 `n` 次运行时间（UTC ISO）。

健康检查：
- `GET /` → `{ "status": "ok" }`。

## 日志
- 输出位置：`logs/scheduler.log`（文件轮转，最大 10MB，保留 5 个备份）。
- 控制台同步输出，便于开发调试。

## 常见问题与排障
- 无法访问受保护页面：确保已登录且浏览器保存了 `access_token` Cookie；API 调用需带 `Authorization: Bearer <token>`。
- SQLite “database is locked”：并发写入时可能出现，系统已设置 `timeout=10` 与行级更新；重试或降低并发。
- Cron 表达式错误：`/api/cron/next` 提示具体错误原因，修正后再试。
- Windows 执行命令：任务命令通过 `subprocess.run(shell=True)` 执行，建议使用可在 `cmd` 下正常执行的命令。
- 密码明文存储：示例项目为演示用途，生产环境需引入密码哈希（如 `bcrypt`）与更安全的用户体系。

## 生产建议
- 更改 `SECRET_KEY` 并迁移到安全的配置管理。
- 为用户密码引入哈希与盐；增加权限体系与审计。
- 将 SQLite 替换为更健壮的数据库（PostgreSQL/MySQL），并引入迁移工具。
- 将执行器隔离为独立进程/队列，避免阻塞与安全风险。
- 增加任务并发控制、速率限制与告警通知。


