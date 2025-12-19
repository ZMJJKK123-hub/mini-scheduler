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
import os
from common.utils import next_run_times
from fastapi.responses import JSONResponse

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


def _parse_task_ids(request: Request, task_ids_form: List[int] | None):
    """Helper: accept either form list 'task_ids' or JSON body list [1,2,3]"""
    # Prefer explicit form parameter
    ids = task_ids_form
    if ids:
        # ensure ints
        try:
            return [int(x) for x in ids]
        except Exception:
            return None

    # Try JSON body
    try:
        body = request.json() if hasattr(request, 'json') else None
        # request.json() in FastAPI Request is coroutine; but when called directly it returns something only in tests.
    except Exception:
        body = None

    try:
        # starlette's Request has .json() as async; but tests send form data so this branch usually won't run.
        # Try synchronous access via request._json if available
        if hasattr(request, '_json'):
            body = request._json
    except Exception:
        pass

    if isinstance(body, list):
        try:
            return [int(x) for x in body]
        except Exception:
            return None

    return None


@app.post("/tasks/bulk/delete")
async def bulk_delete_tasks(request: Request):
    """批量删除任务及其执行记录；支持表单参数 task_ids 或 JSON body 列表"""
    ids = None
    # Try form first
    try:
        form = await request.form()
        if 'task_ids' in form:
            ids = form.getlist('task_ids')
    except Exception:
        form = None

    # Try JSON body
    if not ids:
        try:
            body = await request.json()
            if isinstance(body, list):
                ids = body
        except Exception:
            pass

    if not ids:
        # Debug: include raw body for diagnosis
        try:
            raw = (await request.body()).decode('utf-8', errors='replace')
        except Exception:
            raw = '<no body>'
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "delete", "success": False, "error": f"未选择任务 - body: {raw}"}
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT id, name FROM tasks WHERE id IN ({','.join(['?']*len(ids))})", tuple(ids))
        found = {row['id']: row['name'] for row in cursor.fetchall()}

        cursor.execute(f"DELETE FROM executions WHERE task_id IN ({','.join(['?']*len(ids))})", tuple(ids))
        deleted_exec_count = cursor.rowcount

        cursor.execute(f"DELETE FROM tasks WHERE id IN ({','.join(['?']*len(ids))})", tuple(ids))
        deleted_task_count = cursor.rowcount

        conn.commit()

        return templates.TemplateResponse(
            "bulk_action_result.html",
            {
                "request": request,
                "action": "delete",
                "success": True,
                "requested_ids": ids,
                "deleted_task_count": deleted_task_count,
                "deleted_exec_count": deleted_exec_count,
                "found": found
            }
        )
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "delete", "success": False, "error": str(e)}
        )
    finally:
        conn.close()


@app.post("/tasks/bulk/pause")
async def bulk_pause_tasks(request: Request):
    """批量将任务设置为 PAUSED；支持表单或 JSON"""
    ids = None
    try:
        form = await request.form()
        if 'task_ids' in form:
            ids = form.getlist('task_ids')
    except Exception:
        pass
    if not ids:
        try:
            body = await request.json()
            if isinstance(body, list):
                ids = body
        except Exception:
            pass

    if not ids:
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "pause", "success": False, "error": "未选择任务"}
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE tasks SET status = 'PAUSED' WHERE id IN ({','.join(['?']*len(ids))})", tuple(ids))
        updated_count = cursor.rowcount
        conn.commit()

        return templates.TemplateResponse(
            "bulk_action_result.html",
            {
                "request": request,
                "action": "pause",
                "success": True,
                "requested_ids": ids,
                "updated_count": updated_count
            }
        )
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "pause", "success": False, "error": str(e)}
        )
    finally:
        conn.close()


@app.post("/tasks/bulk/force_run")
async def bulk_force_run_tasks(request: Request):
    """批量强制执行：设置 force_run_at 为当前时间；支持表单或 JSON"""
    ids = None
    try:
        form = await request.form()
        if 'task_ids' in form:
            ids = form.getlist('task_ids')
    except Exception:
        pass
    if not ids:
        try:
            body = await request.json()
            if isinstance(body, list):
                ids = body
        except Exception:
            pass

    if not ids:
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "force_run", "success": False, "error": "未选择任务"}
        )

    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE tasks SET force_run_at = ? WHERE id IN ({','.join(['?']*len(ids))})", (now, *ids))
        updated_count = cursor.rowcount
        conn.commit()

        return templates.TemplateResponse(
            "bulk_action_result.html",
            {
                "request": request,
                "action": "force_run",
                "success": True,
                "requested_ids": ids,
                "updated_count": updated_count,
                "trigger_time": now
            }
        )
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "force_run", "success": False, "error": str(e)}
        )
    finally:
        conn.close()




@app.post("/tasks/{task_id}/run")
def force_run_task(task_id: int, request: Request):
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get task info
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        
        if not task_row:
            return templates.TemplateResponse(
                "run_task_result.html",
                {
                    "request": request,
                    "task_id": task_id,
                    "success": False,
                    "error": f"Task {task_id} not found"
                }
            )
        
        task = dict(task_row)

        cursor.execute(
            "UPDATE tasks SET force_run_at = ? WHERE id = ?",
            (now, task_id)
        )

        if cursor.rowcount == 0:
            return templates.TemplateResponse(
                "run_task_result.html",
                {
                    "request": request,
                    "task_id": task_id,
                    "success": False,
                    "error": "Failed to update task"
                }
            )

        conn.commit()

        return templates.TemplateResponse(
            "run_task_result.html",
            {
                "request": request,
                "task_id": task_id,
                "task_name": task.get("name"),
                "success": True,
                "trigger_time": now
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "run_task_result.html",
            {
                "request": request,
                "task_id": task_id,
                "success": False,
                "error": str(e)
            }
        )
    finally:
        conn.close()


@app.get("/executions/{execution_id}")
def get_execution_detail(execution_id: int):
    execution = get_execution(execution_id)

    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution


@app.get('/api/cron/next')
def api_cron_next(cron: str, n: int = 5):
    try:
        n = int(n)
        if n <= 0 or n > 100:
            raise ValueError('n must be 1..100')
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid parameter n"})

    try:
        times = next_run_times(cron, count=n)
        return {"next_runs": times}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})



# Deepseek generation API removed (feature deprecated)


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
    # 直接从数据库获取任务，而不是从列表中筛选
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取任务
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task_row = cursor.fetchone()
    
    if not task_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 转换为字典
    task = dict(task_row)
    
    # 获取执行记录
    cursor.execute(
        "SELECT * FROM executions WHERE task_id = ? ORDER BY id DESC LIMIT 20",
        (task_id,)
    )
    executions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    # 计算下次运行时间（如Cron表达式无效则忽略）
    next_runs = None
    try:
        next_runs = next_run_times(task.get('cron', ''), count=5)
    except Exception:
        next_runs = None

    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "task": task,
            "executions": executions,
            "next_runs": next_runs
        }
    )



@app.get("/ui/executions/{execution_id}")
def ui_execution_detail(execution_id: int, request: Request):
    execution = get_execution(execution_id)
    
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Get task info for command display
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (execution["task_id"],))
    task_row = cursor.fetchone()
    task = dict(task_row) if task_row else None
    conn.close()
    
    return templates.TemplateResponse(
        "execution_detail.html",
        {
            "request": request,
            "execution": execution,
            "task": task
        }
    )


@app.post("/tasks/{task_id}/toggle")
def toggle_task_status(task_id: int, request: Request):
    """
    切换任务状态并显示结果页面
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 获取当前任务状态
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        
        if not task_row:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        task = dict(task_row)
        current_status = task["status"]
        
        # 2. 确定新状态
        if current_status == "PAUSED":
            new_status = "ACTIVE"
        else:
            new_status = "PAUSED"
        
        # 3. 更新数据库
        cursor.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (new_status, task_id)
        )
        conn.commit()
        
        # 4. 返回结果页面
        return templates.TemplateResponse(
            "toggle_task_result.html",
            {
                "request": request,
                "task_id": task_id,
                "task_name": task.get("name"),
                "old_status": current_status,
                "new_status": new_status,
                "success": True
            }
        )
        
    except sqlite3.Error as e:
        conn.rollback()
        return templates.TemplateResponse(
            "toggle_task_result.html",
            {
                "request": request,
                "task_id": task_id,
                "success": False,
                "error": f"Database error: {str(e)}"
            }
        )
        
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


@app.post("/tasks/{task_id}/delete")
def delete_task(task_id: int, request: Request):
    """
    删除任务及其所有执行记录
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 验证任务是否存在
        cursor.execute("SELECT name FROM tasks WHERE id = ?", (task_id,))
        task_row = cursor.fetchone()
        if not task_row:
            return templates.TemplateResponse(
                "delete_task_result.html",
                {
                    "request": request,
                    "task_id": task_id,
                    "success": False,
                    "error": f"任务 {task_id} 不存在"
                }
            )
        
        task_name = task_row["name"]
        
        # 2. 删除执行记录
        cursor.execute("DELETE FROM executions WHERE task_id = ?", (task_id,))
        deleted_exec_count = cursor.rowcount
        
        # 3. 删除任务
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        
        conn.commit()
        
        return templates.TemplateResponse(
            "delete_task_result.html",
            {
                "request": request,
                "task_id": task_id,
                "task_name": task_name,
                "deleted_exec_count": deleted_exec_count,
                "success": True
            }
        )
        
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return templates.TemplateResponse(
            "delete_task_result.html",
            {
                "request": request,
                "task_id": task_id,
                "success": False,
                "error": str(e)
            }
        )
    finally:
        if conn:
            conn.close()


@app.post("/tasks/bulk/delete")
def bulk_delete_tasks(request: Request, task_ids: List[int] = Form(None)):
    """批量删除任务及其执行记录"""
    if not task_ids:
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "delete", "success": False, "error": "未选择任务"}
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 获取任务名用于展示
        cursor.execute(f"SELECT id, name FROM tasks WHERE id IN ({','.join(['?']*len(task_ids))})", tuple(task_ids))
        found = {row['id']: row['name'] for row in cursor.fetchall()}

        # 删除执行记录
        cursor.execute(f"DELETE FROM executions WHERE task_id IN ({','.join(['?']*len(task_ids))})", tuple(task_ids))
        deleted_exec_count = cursor.rowcount

        # 删除任务
        cursor.execute(f"DELETE FROM tasks WHERE id IN ({','.join(['?']*len(task_ids))})", tuple(task_ids))
        deleted_task_count = cursor.rowcount

        conn.commit()

        return templates.TemplateResponse(
            "bulk_action_result.html",
            {
                "request": request,
                "action": "delete",
                "success": True,
                "requested_ids": task_ids,
                "deleted_task_count": deleted_task_count,
                "deleted_exec_count": deleted_exec_count,
                "found": found
            }
        )
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "delete", "success": False, "error": str(e)}
        )
    finally:
        conn.close()


@app.post("/tasks/bulk/pause")
def bulk_pause_tasks(request: Request, task_ids: List[int] = Form(None)):
    """批量将任务设置为 PAUSED"""
    if not task_ids:
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "pause", "success": False, "error": "未选择任务"}
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE tasks SET status = 'PAUSED' WHERE id IN ({','.join(['?']*len(task_ids))})", tuple(task_ids))
        updated_count = cursor.rowcount
        conn.commit()

        return templates.TemplateResponse(
            "bulk_action_result.html",
            {
                "request": request,
                "action": "pause",
                "success": True,
                "requested_ids": task_ids,
                "updated_count": updated_count
            }
        )
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "pause", "success": False, "error": str(e)}
        )
    finally:
        conn.close()


@app.post("/tasks/bulk/force_run")
def bulk_force_run_tasks(request: Request, task_ids: List[int] = Form(None)):
    """批量强制执行：设置 force_run_at 为当前时间"""
    if not task_ids:
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "force_run", "success": False, "error": "未选择任务"}
        )

    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"UPDATE tasks SET force_run_at = ? WHERE id IN ({','.join(['?']*len(task_ids))})", (now, *task_ids))
        updated_count = cursor.rowcount
        conn.commit()

        return templates.TemplateResponse(
            "bulk_action_result.html",
            {
                "request": request,
                "action": "force_run",
                "success": True,
                "requested_ids": task_ids,
                "updated_count": updated_count,
                "trigger_time": now
            }
        )
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        return templates.TemplateResponse(
            "bulk_action_result.html",
            {"request": request, "action": "force_run", "success": False, "error": str(e)}
        )
    finally:
        conn.close()




