from datetime import datetime
from typing import List
from croniter import croniter


def next_run_times(cron_expr: str, count: int = 5, start_time: datetime | None = None) -> List[str]:
    """Return next `count` run times in ISO format (UTC) for a given cron expression."""
    if start_time is None:
        start_time = datetime.utcnow()

    try:
        it = croniter(cron_expr, start_time)
    except Exception as e:
        raise ValueError(f"Invalid cron expression: {e}")

    times = []
    for _ in range(count):
        nxt = it.get_next(datetime)
        times.append(nxt.isoformat())

    return times
