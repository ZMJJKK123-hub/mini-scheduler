from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Task:
    id:int
    name:str
    cron:str
    command:str
    status:str
    last_run_at:Optional[str]
    created_at:str

    @staticmethod
    def now():
        return datetime.utcnow().isoformat()