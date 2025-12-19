from common.db import get_connection
from datetime import datetime, timedelta

conn = get_connection()
cursor = conn.cursor()

fake_time = (datetime.utcnow() - timedelta(minutes=10)).isoformat()

cursor.execute(
    """
    UPDATE tasks
    SET status = 'RUNNING',
        last_run_at = ?
    WHERE id = 1
    """,
    (fake_time,)
)

conn.commit()
conn.close()

print("已制造僵尸 RUNNING 任务")