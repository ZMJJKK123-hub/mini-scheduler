# Mini Scheduler - 任务调度系统

一个基于 FastAPI 的轻量级任务调度系统，支持 cron 表达式、任务监控、用户认证等功能。

## 功能特性

- ✅ **任务管理**: 创建、编辑、删除定时任务
- ✅ **Cron 调度**: 支持标准的 cron 表达式
- ✅ **实时监控**: 任务状态监控和执行日志
- ✅ **用户认证**: JWT 身份验证和注册功能
- ✅ **重试机制**: 失败任务自动重试
- ✅ **搜索与分页**: 任务列表搜索和分页显示
- ✅ **批量操作**: 支持批量删除、暂停、强制执行
- ✅ **Web 界面**: 现代化的响应式 UI
- ✅ **API 接口**: RESTful API 支持

## 技术栈

- **后端**: FastAPI, Uvicorn
- **数据库**: SQLite
- **调度**: croniter, threading
- **前端**: Jinja2 模板, 原生 JavaScript
- **认证**: JWT (jose)
- **样式**: Font Awesome, 自定义 CSS

## 安装

### 环境要求

- Python 3.8+
- pip

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd mini-scheduler
```

2. 创建虚拟环境
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或在 Windows: .venv\Scripts\activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

## 运行

### 开发模式

```bash
python3 -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 生产模式

```bash
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

访问 http://127.0.0.1:8000 打开应用。

## 使用

### 首次使用

1. 打开浏览器访问 http://127.0.0.1:8000
2. 使用演示账号登录：
   - 用户名: `admin`
   - 密码: `admin123`
3. 或点击"注册"创建新账号

### 创建任务

1. 在任务列表页点击"新建任务"
2. 填写任务信息：
   - 名称: 任务的显示名称
   - Cron 表达式: 定时规则 (例如: `*/5 * * * *` 每5分钟执行)
   - 命令: 要执行的 shell 命令

### 任务管理

- **执行**: 立即执行任务
- **暂停/恢复**: 控制任务调度状态
- **编辑**: 修改任务信息
- **删除**: 删除任务及其执行记录

### 搜索和过滤

- 使用搜索框按名称或命令搜索
- 使用状态标签过滤任务

## API 文档

启动服务后访问 http://127.0.0.1:8000/docs 查看完整的 API 文档。

### 主要 API 端点

#### 认证
- `POST /auth/login` - 用户登录
- `POST /auth/register` - 用户注册
- `GET /auth/me` - 获取当前用户信息

#### 任务管理
- `GET /ui/tasks` - 任务列表页面
- `POST /ui/tasks/create` - 创建任务
- `GET /ui/tasks/{id}` - 任务详情
- `POST /ui/tasks/{id}/update` - 更新任务
- `POST /tasks/{id}/run` - 强制执行任务

#### 批量操作
- `POST /tasks/bulk/delete` - 批量删除
- `POST /tasks/bulk/pause` - 批量暂停
- `POST /tasks/bulk/force_run` - 批量强制执行

## 数据库

项目使用 SQLite 数据库，文件位于项目根目录的 `scheduler.db`。

### 数据库表结构

- `tasks`: 任务表
- `executions`: 执行记录表
- `users`: 用户表 (演示用，生产环境请使用真实数据库)

## 配置

### 环境变量

- `SECRET_KEY`: JWT 密钥 (默认随机生成)

### 日志

日志文件位于 `logs/scheduler.log`，包含调度器和任务执行信息。

## 开发

### 项目结构

```
mini-scheduler/
├── api/
│   ├── main.py          # FastAPI 应用主文件
│   └── __init__.py
├── common/
│   ├── auth.py          # 认证模块
│   ├── db.py            # 数据库操作
│   ├── models.py        # 数据模型
│   └── utils.py         # 工具函数
├── scheduler/
│   ├── scheduler.py     # 调度器核心
│   └── __init__.py
├── templates/           # Jinja2 模板
├── tests/               # 测试文件
├── worker/              # 工作进程
├── config.py            # 配置
├── requirements.txt     # 依赖
└── README.md           # 本文件
```

### 添加新功能

1. 在 `api/main.py` 添加路由
2. 在 `common/db.py` 添加数据库操作
3. 在 `templates/` 添加对应模板
4. 更新 `requirements.txt` 如果需要新依赖

## 测试

运行测试：

```bash
python3 -m pytest tests/
```

## 部署

### 使用 Docker

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 生产部署注意事项

1. 使用生产级数据库 (PostgreSQL/MySQL)
2. 配置 HTTPS
3. 设置环境变量
4. 使用反向代理 (nginx)
5. 配置日志轮转
6. 设置监控和告警

## 故障排除

### 常见问题

1. **端口占用**: 确保 8000 端口未被占用
2. **权限问题**: 确保有执行 shell 命令的权限
3. **数据库错误**: 检查 `scheduler.db` 文件权限
4. **登录问题**: 清除浏览器缓存或使用无痕模式

### 日志查看

```bash
tail -f logs/scheduler.log
```

## 贡献

欢迎提交 Issue 和 Pull Request！

### 开发规范

- 使用 Black 格式化代码
- 添加适当的测试
- 更新文档

## 许可证

MIT License

## 联系

如有问题请提交 Issue 或联系维护者。
│ └── scheduler.py # 任务调度器
├── templates/ # HTML模板文件
│ ├── base.html # 基础模板
│ ├── tasks.html # 任务列表页面
│ ├── task_detail.html # 任务详情页面
│ ├── create_task.html # 创建任务页面
│ ├── execution_detail.html # 执行详情页面
│ ├── bulk_action_result.html # 批量操作结果
│ ├── run_task_result.html # 执行任务结果
│ ├── toggle_task_result.html # 切换状态结果
│ └── delete_task_result.html # 删除任务结果
├── data/ # 数据目录
│ └── scheduler.db # SQLite数据库
├── requirements.txt # 依赖文件
└── README.md # 项目说明

text

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip 包管理工具

### 1. 安装依赖
```bash
pip install fastapi uvicorn sqlite3 croniter jinja2
2. 启动应用
bash
# 启动开发服务器
uvicorn app:app --reload --host 0.0.0.0 --port 8000
3. 访问应用
Web 界面：http://localhost:8000/ui/tasks

API 文档：http://localhost:8000/docs

健康检查：http://localhost:8000/

📖 使用指南
创建任务
访问 http://localhost:8000/ui/tasks/create

填写任务信息：

名称：任务名称

Cron 表达式：定时规则（如 */5 * * * * 表示每5分钟执行）

命令：要执行的 Shell 命令

管理任务
查看任务：主页显示所有任务

切换状态：点击任务的状态按钮切换激活/暂停

强制执行：点击"立即执行"按钮

查看日志：点击任务查看执行历史

Cron 表达式示例
*/5 * * * * - 每5分钟

0 * * * * - 每小时

0 0 * * * - 每天午夜

0 9 * * 1 - 每周一上午9点

🔧 API 接口
任务管理
GET /tasks - 获取所有任务

POST /tasks - 创建新任务

GET /tasks/{task_id} - 获取任务详情

POST /tasks/{task_id}/run - 强制执行任务

POST /tasks/{task_id}/toggle - 切换任务状态

POST /tasks/{task_id}/cleanup - 清理执行记录

POST /tasks/{task_id}/delete - 删除任务

批量操作
POST /tasks/bulk/delete - 批量删除任务

POST /tasks/bulk/pause - 批量暂停任务

POST /tasks/bulk/force_run - 批量强制执行

执行记录
GET /executions/{execution_id} - 获取执行详情

GET /api/executions/{execution_id} - API 方式获取执行详情

工具接口
GET /api/cron/next - 获取 cron 表达式下次执行时间

GET / - 健康检查

🎯 任务状态说明
状态	说明
ACTIVE	任务激活，按计划执行
PAUSED	任务暂停，不执行
RUNNING	任务正在执行中
PENDING	任务待执行
FAILED	任务执行失败
⚙️ 配置说明
数据库配置
数据库文件默认位置：data/scheduler.db

自动创建数据库表

支持并发访问

自动迁移字段

调度器配置
检查间隔：30秒

运行超时：1分钟

最大保留执行记录：50条（可配置）

🔍 调度器工作原理
调度循环：每30秒检查一次所有任务

时间计算：根据 cron 表达式计算下次执行时间

状态检查：只有 ACTIVE/PENDING/FAILED 状态的任务会被调度

并发控制：使用数据库锁防止任务重复执行

异步执行：每个任务在独立线程中执行

结果记录：记录执行输出和错误信息

📊 数据库表结构
tasks 表
字段	类型	说明
id	INTEGER	主键
name	TEXT	任务名称
cron	TEXT	cron 表达式
command	TEXT	执行的命令
status	TEXT	任务状态
last_run_at	TEXT	上次执行时间
created_at	TEXT	创建时间
force_run_at	TEXT	强制执行时间
last_error	TEXT	最后错误信息
executions 表
字段	类型	说明
id	INTEGER	主键
task_id	INTEGER	关联任务ID
status	TEXT	执行状态
started_at	TEXT	开始时间
finished_at	TEXT	结束时间
stdout	TEXT	标准输出
stderr	TEXT	错误输出
error	TEXT	错误信息
🛠️ 开发说明
添加新功能
在 app.py 中添加新的路由

在 common/db.py 中添加数据库操作

在 templates/ 中添加对应的 HTML 模板

在 scheduler/scheduler.py 中修改调度逻辑（如需要）

测试 API
bash
# 创建任务
curl -X POST "http://localhost:8000/tasks" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试任务","cron":"*/5 * * * *","command":"echo hello"}'

# 获取所有任务
curl "http://localhost:8000/tasks"

# 强制执行任务
curl -X POST "http://localhost:8000/tasks/1/run"
📝 注意事项
时间格式：所有时间使用 UTC 时间，存储为 ISO 格式字符串

并发安全：使用数据库事务确保数据一致性

命令安全：系统会执行任意 Shell 命令，请确保命令来源可信

资源限制：长时间运行的任务可能占用系统资源

日志查看：执行记录保存在数据库中，可定期清理

🤝 贡献指南
Fork 项目

创建功能分支

提交更改

推送分支

创建 Pull Request

📄 许可证
MIT License

text

可以直接复制上面的所有内容到你的 `README.md` 文件中。这是完整的 Markdown 格式文档，包含所有必要的信息。

