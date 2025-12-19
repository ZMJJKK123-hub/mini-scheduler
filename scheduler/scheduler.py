import time
from croniter import croniter
from datetime import datetime
from common.db import list_tasks, get_connection, create_execution, finish_execution
from common.models import Task
from datetime import timedelta
import subprocess
import threading
from common.db import try_mark_running

#uvicorn api.main:app --reload

RUNNING_TIMEOUT = timedelta(minutes=1)

SCHEDULABLE_STATUSES = {"PENDING", "ACTIVE", "FAILED"}

# 获取任务的基准时间    
def get_base_time(task: Task) -> datetime:
    if task.last_run_at:
        return datetime.fromisoformat(task.last_run_at)
    return datetime.fromisoformat(task.created_at)

# 任务调度器
def run_scheduler():
    while True:
        print("Scheduler started\n")  # 添加日志
        now = datetime.utcnow()
        tasks = list_tasks()

        for task in tasks:

            if task.status == "RUNNING" and task.last_run_at:
                last_run = datetime.fromisoformat(task.last_run_at)
                if now - last_run > RUNNING_TIMEOUT:
                    print(f"任务 {task.id} RUNNING 超时，恢复为 FAILED")
                    update_task_status(
                        task_id=task.id,
                        status="FAILED"
                    )
                    continue

            # 获取上一次执行时间
            base_time = get_base_time(task)

            try:
                next_run_time = croniter(task.cron, base_time).get_next(datetime)
            except Exception as e:
                print(f"任务 {task.id} 的 cron 表达式无效: {task.cron}, 错误: {e}")

                update_task_status(
                    task_id=task.id,
                    status="FAILED",
                    last_error=f"invalid cron: {e}"
                )
                continue
            # 判断是否强制执行
            should_run = (
                    next_run_time <= now
                    or (task.force_run_at and datetime.fromisoformat(task.force_run_at) <= now)
                )
            # 判断任务状态为 PENDING 且当前时间大于或等于下一次执行时间
            if task.status in SCHEDULABLE_STATUSES and should_run:
                print(f"task {task.id} is executing mission")
                print(f"当前任务的状态是{task.status}")
                start_time = datetime.utcnow().isoformat()

                if not try_mark_running(task.id, start_time):
                    continue  # 没抢到，跳过

                execution_id = create_execution(
                    task_id=task.id,
                    started_at=datetime.utcnow().isoformat(),
                    status="QUEUED"
                )

                threading.Thread(
                    target=execute_task,
                    args=(task,execution_id),
                    daemon=True
                ).start()

            else:
                print(f"这是第{task.id}个程序不选择运行")
                print(f"现在task的状况是{task.status}")
                print(f"时间是否允许的情况是{next_run_time <= now}")
                print(f"当前时间是{now},下次运行时间是{next_run_time}")
                print("\n")
        
        time.sleep(30)  # 每分钟检查一次

def execute_task(task: Task, execution_id: int):
    start_time= datetime.utcnow().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
    "UPDATE executions SET status='RUNNING' WHERE id=?",
    (execution_id,)
)
    conn.commit()
    conn.close()

    print(f"任务 {task.id} 执行于 {start_time}")
    print(f"Command: {task.command}")

    try:
        result = subprocess.run(
        task.command,
        shell=True,
        capture_output=True,
        text=True)

        finished_at = datetime.utcnow().isoformat()

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        if result.returncode == 0:
            execution_status = "SUCCESS"
            task_status = "ACTIVE"
        else:
            execution_status = "FAILED"
            task_status = "FAILED"

        finish_execution(
            execution_id=execution_id,
            status=execution_status,
            finished_at=finished_at,
            stdout=result.stdout,
            stderr=result.stderr
        )

        update_task_status(
            task_id=task.id,
            status=task_status,
            force_run_at=None
        )

    except Exception as e:
        finished_at = datetime.utcnow().isoformat()

        finish_execution(
            execution_id=execution_id,
            status="FAILED",
            finished_at=finished_at,
            error=str(e)
        )

        update_task_status(
            task_id=task.id,
            status="FAILED",
            force_run_at=None
        )




def update_task_status(
    task_id: int,
    status: str | None = None,
    last_run_at: str | None = None,
    last_error: str | None = None,
    force_run_at: str | None = None
):
    conn = get_connection()
    cursor = conn.cursor()

    if status is not None:
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id)
        )

    if last_run_at is not None:
        cursor.execute(
            "UPDATE tasks SET last_run_at = ? WHERE id = ?",
            (last_run_at, task_id)
        )

    if last_error is not None:
        cursor.execute(
            "UPDATE tasks SET last_error = ? WHERE id = ?",
            (last_error, task_id)
        )

    if force_run_at is not None:
        cursor.execute(
            "UPDATE tasks SET force_run_at = ? WHERE id = ?",
            (force_run_at, task_id)
        )
    else:
        cursor.execute(
            "UPDATE tasks SET force_run_at = NULL WHERE id = ?",
            (task_id,)
        )

    conn.commit()
    conn.close()

    print(f"任务 {task_id} 更新完成")
    

