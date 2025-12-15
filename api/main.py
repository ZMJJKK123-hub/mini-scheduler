from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from common.models import Task
from common.db import create_task, list_tasks, init_db
import threading
from scheduler.scheduler import run_scheduler

app=FastAPI()

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

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

