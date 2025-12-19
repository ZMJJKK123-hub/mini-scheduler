import sqlite3
from pathlib import Path
from common.models import Task
from datetime import datetime

DB_PATH=Path("data/scheduler.db")

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,          # 👈 等待锁（秒）
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor=conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cron TEXT NOT NULL,
            command TEXT NOT NULL,
            status TEXT NOT NULL ,
            last_run_at TEXT,
            created_at TEXT NOT NULL
            
            )
""")
        try:
            cursor.execute(
                "ALTER TABLE tasks ADD COLUMN force_run_at TEXT"
            )
        except sqlite3.OperationalError:
            pass  # 字段已存在，忽略
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT ,
            finished_at TEXT,
            stdout TEXT,
            stderr TEXT,
            error TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )
        """)
        
def create_task(name:str,cron:str,command:str)->Task:
    with get_connection() as conn:
        cursor=conn.cursor()
        now=Task.now()

        cursor.execute(
            
            """
INSERT INTO tasks (name,cron,command,status,last_run_at,created_at)
VALUES(?,?,?,?,?,?)
            """,
(name,cron,command,"PENDING",None,now)       
                       )
        task_id=cursor.lastrowid

    return Task(
        id=task_id,
        name=name,
        cron=cron,
        command=command,
        status="PENDING",
        last_run_at=None,
        created_at=now
    )


def list_tasks()->list[Task]:
    with get_connection() as conn:
        cursor=conn.cursor()
        
        rows=cursor.execute("SELECT * FROM tasks").fetchall()
        
        return [Task(**dict(row))for row in rows] 
    

def try_mark_running(task_id: int, start_time: str) -> bool:
    """
    尝试把任务从非 RUNNING 状态标记为 RUNNING
    返回 True 表示抢占成功
    返回 False 表示已经被抢占
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE tasks
        SET status = 'RUNNING',
            last_run_at = ?
        WHERE id = ?
        AND status != 'RUNNING'
        """,
        (start_time, task_id)
    )

    success = cursor.rowcount == 1
    conn.commit()
    conn.close()

    return success

        
def create_execution(task_id: int, started_at: str | None, status: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO executions (task_id, status, started_at)
        VALUES (?, ?, ?)
        """,
        (task_id, status, started_at)
    )

    execution_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return execution_id


def finish_execution(
    execution_id: int,
    status: str,
    finished_at: str,
    stdout: str | None = None,
    stderr: str | None = None,
    error: str | None = None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE executions
        SET status = ?,
            finished_at = ?,
            stdout = ?,
            stderr = ?,
            error = ?
        WHERE id = ?
        """,
        (status, finished_at, stdout, stderr, error, execution_id)
    )

    conn.commit()
    conn.close()


def fail_execution(execution_id: int, error: str):
    finish_execution(
        execution_id=execution_id,
        status="FAILED",
        finished_at=datetime.utcnow().isoformat(),
        error=error
    )



def get_execution(execution_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT * FROM executions WHERE id = ?",
        (execution_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)



def list_executions_by_task(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute(
        """
        SELECT *
        FROM executions
        WHERE task_id = ?
        ORDER BY id DESC
        LIMIT 20
        """,
        (task_id,)
    ).fetchall()

    conn.close()
    return [dict(row) for row in rows]