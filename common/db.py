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
        
        # 添加重试字段
        try:
            cursor.execute(
                "ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute(
                "ALTER TABLE tasks ADD COLUMN max_retries INTEGER DEFAULT 3"
            )
        except sqlite3.OperationalError:
            pass
        
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
        
        # 创建用户表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            disabled BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL
        )
        """)
        
        # 创建默认管理员用户（如果不存在）
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", ("admin",))
        if cursor.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO users (username, password, email, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
                ("admin", "admin123", "admin@example.com", "Admin User", now)
            )
        
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


def search_tasks(query: str = "", status: str = "", limit: int = 20, offset: int = 0) -> tuple[list[Task], int]:
    """搜索任务，返回 (任务列表, 总数)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if query:
            conditions.append("(name LIKE ? OR command LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 获取总数
        count_query = f"SELECT COUNT(*) as cnt FROM tasks WHERE {where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()['cnt']
        
        # 获取分页数据
        query_str = f"SELECT * FROM tasks WHERE {where_clause} ORDER BY id DESC LIMIT ? OFFSET ?"
        cursor.execute(query_str, params + [limit, offset])
        rows = cursor.fetchall()
        
        return [Task(**dict(row)) for row in rows], total


def get_task_by_id(task_id: int) -> Task | None:
    """根据 ID 获取任务"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        
        if row:
            return Task(**dict(row))
        return None


def update_task(task_id: int, name: str = None, cron: str = None, command: str = None) -> bool:
    """更新任务信息"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        
        if cron is not None:
            updates.append("cron = ?")
            params.append(cron)
        
        if command is not None:
            updates.append("command = ?")
            params.append(command)
        
        if not updates:
            return False
        
        params.append(task_id)
        update_str = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(update_str, params)
        conn.commit()
        
        return cursor.rowcount > 0 


def increment_retry_count(task_id: int) -> int:
    """增加任务重试计数，返回新的重试计数"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE tasks SET retry_count = retry_count + 1 WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    
    # 获取新的重试计数
    cursor.execute("SELECT retry_count FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    return row['retry_count'] if row else 0


def reset_retry_count(task_id: int):
    """重置任务重试计数"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE tasks SET retry_count = 0 WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()


def get_task_retry_info(task_id: int) -> dict:
    """获取任务重试信息"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT retry_count, max_retries FROM tasks WHERE id = ?",
        (task_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "retry_count": row['retry_count'],
            "max_retries": row['max_retries']
        }
    return {"retry_count": 0, "max_retries": 3}

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


# 用户相关数据库操作
def create_user_db(username: str, password: str, email: str = None, full_name: str = None) -> tuple[bool, str]:
    """在数据库中创建用户"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查用户是否已存在
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False, "用户已存在"
            
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO users (username, password, email, full_name, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, password, email or f"{username}@example.com", full_name or username, now)
            )
            
            conn.commit()
            return True, "创建成功"
    except Exception as e:
        return False, f"数据库错误: {str(e)}"


def get_user_by_username(username: str):
    """根据用户名获取用户"""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()
            
            if row:
                return dict(row)
            return None
    except Exception:
        return None


def authenticate_user_db(username: str, password: str):
    """验证用户登录"""
    user = get_user_by_username(username)
    if not user:
        return False
    
    # 简单密码验证（生产环境应该使用哈希）
    if user["password"] == password:
        return user
    
    return False



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