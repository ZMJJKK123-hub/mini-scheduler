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
    last_error: Optional[str] = None
    force_run_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3 

    @staticmethod
    def now():
        return datetime.utcnow().isoformat()