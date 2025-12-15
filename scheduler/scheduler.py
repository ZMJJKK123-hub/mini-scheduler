import time
from croniter import croniter
from datetime import datetime
from common.db import list_tasks, get_connection
from common.models import Task
from datetime import timedelta
import subprocess

RUNNING_TIMEOUT = timedelta(minutes=5)

# 获取任务的基准时间    
def get_base_time(task: Task) -> datetime:
    if task.last_run_at:
        return datetime.fromisoformat(task.last_run_at)
    return datetime.fromisoformat(task.created_at)

# 任务调度器
def run_scheduler():
    while True:
        print("Scheduler started")  # 添加日志
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
                
            # 获取下一次执行时间
            base_time = get_base_time(task)
            next_run_time = croniter(task.cron, base_time).get_next(datetime)
            
            # 判断任务状态为 PENDING 且当前时间大于或等于下一次执行时间
            if task.status != "RUNNING" and next_run_time<= now:
                print(f"task {task.id} is executing mission")
                print(f"当前任务的状态是{task.status}")
                execute_task(task)
            else:
                print(f"这是第{task.id}个程序不选择运行")
                print(f"现在task的状况是{task.status}")
                print(f"时间是否允许的情况是{next_run_time <= now}")
                print(f"当前时间是{now},下次运行时间是{next_run_time}")
                print("\n")
        
        time.sleep(60)  # 每分钟检查一次

def execute_task(task: Task):
    start_time= datetime.utcnow().isoformat()
    print(f"任务 {task.id} 执行于 {start_time}")
    print(f"Command: {task.command}")


    update_task_status(
        task_id=task.id,
        status="RUNNING",
        last_run_at=start_time
    )

    result = subprocess.run(
    task.command,
    shell=True,
    capture_output=True,
    text=True)

    print("stdout:")
    print(result.stdout)

    print("stderr:")
    print(result.stderr)

    if result.returncode == 0:
        final_status = "ACTIVE"
    else:
        final_status = "FAILED"


    update_task_status(
        task_id=task.id,
        status=final_status
    )

    print(f"任务 {task.id} 执行结束，状态：{final_status}")
    print("\n")



def update_task_status(
    task_id: int,
    status: str | None = None,
    last_run_at: str | None = None
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

    conn.commit()
    conn.close()

    print(f"任务 {task_id} 更新完成")
    

