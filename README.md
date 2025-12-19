# Cron 任务调度系统

## 📋 项目概述
这是一个基于 FastAPI 的分布式 Cron 任务调度系统，提供完整的任务管理、调度执行和监控功能。系统支持 Web 界面和 REST API 接口，可以方便地创建、管理和监控定时任务。

## ✨ 功能特性

### 核心功能
- **任务管理**：创建、查看、修改、删除定时任务
- **Cron 表达式支持**：标准的 cron 表达式格式，支持预览下次执行时间
- **任务调度**：后台调度器自动执行定时任务
- **批量操作**：支持批量删除、暂停、强制执行任务
- **执行记录**：查看任务执行历史记录和详情
- **状态管理**：任务激活/暂停状态切换
- **Web 界面**：友好的 Web 管理界面
- **REST API**：完整的 API 接口支持
- **数据清理**：自动清理旧的执行记录

### 高级功能
- **强制执行**：立即触发任务执行
- **状态切换**：灵活的任务状态管理
- **Cron 预览**：查看 cron 表达式的下次执行时间
- **并发控制**：防止任务重复执行
- **超时处理**：自动检测并处理超时任务
- **Shell 命令支持**：执行任意 Shell 命令

## 🏗️ 技术栈

### 后端
- **框架**：FastAPI
- **数据库**：SQLite
- **Cron 解析**：croniter
- **进程管理**：subprocess
- **并发处理**：threading

### 前端
- **模板引擎**：Jinja2
- **样式框架**：Bootstrap 5
- **JavaScript**：原生 JS

## 📁 项目结构
cron-scheduler/
├── app.py # 主应用文件 (FastAPI应用)
├── common/ # 公共模块
│ ├── init.py
│ ├── db.py # 数据库操作
│ ├── models.py # 数据模型
│ └── utils.py # 工具函数
├── scheduler/ # 调度器模块
│ ├── init.py
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

