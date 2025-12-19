import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from api.main import app
client=TestClient(app)
# create tasks
r1=client.post('/tasks', json={'name':'t1','cron':'* * * * *','command':'echo'})
print('create1', r1.status_code, r1.json())
r2=client.post('/tasks', json={'name':'t2','cron':'* * * * *','command':'echo'})
print('create2', r2.status_code, r2.json())
# try bulk delete
resp = client.post('/tasks/bulk/delete', data=[('task_ids', str(r1.json()['id'])), ('task_ids', str(r2.json()['id']))])
print('bulk delete status', resp.status_code)
print('headers', resp.headers)
print(resp.text)
