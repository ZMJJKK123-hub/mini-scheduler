import time
from croniter import croniter
from datetime import datetime
from common.db import (
    list_tasks, get_connection, create_execution, finish_execution,
    try_mark_running, increment_retry_count, reset_retry_count,
    get_task_retry_info
)
from common.models import Task
from datetime import timedelta
import subprocess
import threading
from config import logger

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
    logger.info("任务调度器已启动")
    while True:
        try:
            now = datetime.utcnow()
            tasks = list_tasks()
            logger.debug(f"调度检查: 扫描 {len(tasks)} 个任务")

            for task in tasks:

                if task.status == "RUNNING" and task.last_run_at:
                    last_run = datetime.fromisoformat(task.last_run_at)
                    if now - last_run > RUNNING_TIMEOUT:
                        logger.warning(f"任务 {task.id} ({task.name}) RUNNING 超时，恢复为 FAILED")
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
                    logger.error(f"任务 {task.id} ({task.name}) 的 cron 表达式无效: {task.cron}, 错误: {e}")

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
                    logger.info(f"触发任务执行: ID={task.id}, name={task.name}, status={task.status}")
                    start_time = datetime.utcnow().isoformat()

                    if not try_mark_running(task.id, start_time):
                        logger.debug(f"任务 {task.id} 已被其他进程占用，跳过")
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
        except Exception as e:
            logger.error(f"调度器异常: {str(e)}", exc_info=True)
        
        time.sleep(5)  # 改为 5 秒轮询一次，提高调度精度

def execute_task(task: Task, execution_id: int):
    start_time= datetime.utcnow().isoformat()
    logger.info(f"开始执行任务 {task.id} ({task.name}): {task.command}")

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
            logger.info(f"任务 {task.id} ({task.name}) 执行成功")
            # 成功则重置重试计数
            reset_retry_count(task.id)
        else:
            execution_status = "FAILED"
            task_status = "FAILED"
            logger.warning(f"任务 {task.id} ({task.name}) 执行失败，返回码: {result.returncode}")
            
            # 尝试重试
            retry_info = get_task_retry_info(task.id)
            if retry_info['retry_count'] < retry_info['max_retries']:
                new_count = increment_retry_count(task.id)
                logger.info(f"任务 {task.id} 重试 {new_count}/{retry_info['max_retries']}")
                task_status = "PENDING"  # 标记为待处理，触发重试

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
        logger.error(f"任务 {task.id} ({task.name}) 执行异常: {str(e)}", exc_info=True)

        finish_execution(
            execution_id=execution_id,
            status="FAILED",
            finished_at=finished_at,
            error=str(e)
        )
        
        # 异常也尝试重试
        retry_info = get_task_retry_info(task.id)
        task_status = "FAILED"
        if retry_info['retry_count'] < retry_info['max_retries']:
            new_count = increment_retry_count(task.id)
            logger.info(f"任务 {task.id} 异常重试 {new_count}/{retry_info['max_retries']}")
            task_status = "PENDING"

        update_task_status(
            task_id=task.id,
            status=task_status,
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
    

