Mini Scheduler
===============

新增功能说明
---------------
- Cron 下次运行时间预览：
	- 在任务创建页面实时展示给定 Cron 表达式的下 5 次运行时间（通过后端 API `/api/cron/next` 计算）。
	- 在任务详情页显示该任务的下 5 次预计运行时间。
	- 使用 `croniter` 进行解析。

	- (已移除) Deepseek AI 生成器（实验性）已从本仓库中删除。

如何使用
----------
- 运行服务：`uvicorn api.main:app --reload`
- 打开创建任务页面：`/ui/tasks/create`，在 Cron 字段输入表达式，预览区域会显示下次运行时间。

