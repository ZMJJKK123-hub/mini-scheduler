import sqlite3
from pathlib import Path
from common.models import Task

DB_PATH=Path("data/scheduler.db")

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
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
    



        
