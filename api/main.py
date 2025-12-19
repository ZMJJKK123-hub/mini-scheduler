from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from common.models import Task
from common.db import create_task, list_tasks, init_db
import threading
from scheduler.scheduler import run_scheduler
from datetime import datetime
from fastapi import HTTPException
from common.db import get_connection, create_execution, get_execution, list_executions_by_task
from fastapi.templating import Jinja2Templates
from fastapi import Request
import sqlite3
from fastapi import Form
from fastapi.responses import RedirectResponse

templates = Jinja2Templates(directory="templates")

app=FastAPI()

@app.on_event("startup")
def startup():
    init_db()
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

@app.get("/")
def health_check():
    return {"status": "ok"}

class TaskCreateRequest(BaseModel):
    name: str
    cron: str
    command: str





@app.post("/tasks")
def create_new_task(task: TaskCreateRequest):
    created_task = create_task(task.name, task.cron, task.command)
    return created_task

@app.get("/tasks", response_model=List[Task])
def get_all_tasks():
    tasks = list_tasks()
    return tasks




@app.post("/tasks/{task_id}/run")
def force_run_task(task_id: int):
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tasks SET force_run_at = ? WHERE id = ?",
        (now, task_id)
    )

    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    conn.commit()
    conn.close()


    return {
        "task_id": task_id,
        "message": "Task triggered"
    }


@app.get("/executions/{execution_id}")
def get_execution_detail(execution_id: int):
    execution = get_execution(execution_id)

    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution


@app.get("/api/executions/{execution_id}")
def api_execution_detail(execution_id: int):
    execution = get_execution(execution_id)

    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution


@app.get("/ui/tasks")
def ui_tasks(request: Request):
    tasks = list_tasks()
    return templates.TemplateResponse(
        "tasks.html",
        {
            "request": request,
            "tasks": tasks
        }
    )


# 显示创建任务表单
@app.get("/ui/tasks/create")
def show_create_task_form(request: Request):
    return templates.TemplateResponse(
        "create_task.html",
        {"request": request}
    )


# 处理表单提交
@app.post("/ui/tasks/create")
def create_task_from_form(
    request: Request,
    name: str = Form(...),
    cron: str = Form(...),
    command: str = Form(...)
):
    # 调用已有的create_task函数
    task = create_task(name, cron, command)
    
    # 重定向到任务列表
    return RedirectResponse(
        url=f"/ui/tasks/{task.id}",  # 或者 "/ui/tasks" 直接回到列表
        status_code=303  # 303 See Other for POST-redirect-GET pattern
    )


@app.get("/ui/tasks/{task_id}")
def ui_task_detail(task_id: int, request: Request):
    tasks = list_tasks()
    task = next((t for t in tasks if t.id == task_id), None)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    executions = list_executions_by_task(task_id)

    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "task": task,
            "executions": executions
        }
    )



@app.get("/ui/executions/{execution_id}")
def ui_execution_detail(execution_id: int, request: Request):
    execution = get_execution(execution_id)
    
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return templates.TemplateResponse(
        "execution_detail.html",
        {
            "request": request,
            "execution": execution
        }
    )


@app.post("/tasks/{task_id}/toggle")
def toggle_task_status(task_id: int):
    """
    切换任务状态：
    - 如果任务状态是 PAUSED，则恢复为 ACTIVE
    - 如果任务状态不是 PAUSED，则暂停为 PAUSED
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 获取当前任务状态
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        current_status = row["status"]
        
        # 2. 确定新状态
        if current_status == "PAUSED":
            # 如果当前是暂停状态，恢复为 ACTIVE
            new_status = "ACTIVE"
        else:
            # 如果当前不是暂停状态，暂停任务
            new_status = "PAUSED"
        
        # 3. 更新数据库
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (new_status, task_id)
        )
        
        # 4. 提交事务
        conn.commit()
        
        # 5. 返回结果
        return {
            "task_id": task_id,
            "old_status": current_status,
            "new_status": new_status,
            "message": f"Task {task_id} status changed from {current_status} to {new_status}"
        }
        
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
    finally:
        conn.close()


@app.post("/tasks/{task_id}/cleanup")
def cleanup_old_executions(
    task_id: int,
    keep_last: int = 50  # 默认保留最近50条
):
    """
    清理任务的旧执行记录
    keep_last: 保留最近多少条记录
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 验证任务是否存在
        cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # 2. 获取清理前的记录数
        cursor.execute("SELECT COUNT(*) as count FROM executions WHERE task_id = ?", (task_id,))
        before_count = cursor.fetchone()["count"]
        
        # 3. 执行清理（保留最近keep_last条）
        cursor.execute("""
            DELETE FROM executions 
            WHERE task_id = ? 
            AND id NOT IN (
                SELECT id FROM executions 
                WHERE task_id = ? 
                ORDER BY id DESC 
                LIMIT ?
            )
        """, (task_id, task_id, keep_last))
        
        deleted_count = cursor.rowcount
        
        # 4. 获取清理后的记录数
        cursor.execute("SELECT COUNT(*) as count FROM executions WHERE task_id = ?", (task_id,))
        after_count = cursor.fetchone()["count"]
        
        conn.commit()
        
        return {
            "task_id": task_id,
            "deleted_count": deleted_count,
            "before_count": before_count,
            "after_count": after_count,
            "keep_last": keep_last,
            "message": f"Deleted {deleted_count} old executions, kept {after_count} recent ones"
        }
        
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Cleanup error: {str(e)}")
        
    finally:
        if conn:
            conn.close()




