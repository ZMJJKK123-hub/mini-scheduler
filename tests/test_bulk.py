import unittest
from fastapi.testclient import TestClient
from api.main import app
from common.db import get_connection

client = TestClient(app)

class BulkActionsTest(unittest.TestCase):
    def setUp(self):
        # Ensure DB is clean for tests: delete all tasks and executions
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM executions")
        cur.execute("DELETE FROM tasks")
        conn.commit()
        conn.close()

    def create_task(self, name="t", cron="* * * * *", command="echo hi"):
        payload = {"name": name, "cron": cron, "command": command}
        r = client.post("/tasks", json=payload)
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_bulk_delete(self):
        t1 = self.create_task("alpha")
        t2 = self.create_task("beta")

        # perform bulk delete
        r = client.post("/tasks/bulk/delete", json=[t1["id"], t2["id"]])
        self.assertEqual(r.status_code, 200)

        # check tasks list
        r = client.get("/tasks")
        self.assertEqual(r.status_code, 200)
        tasks = r.json()
        ids = [t["id"] for t in tasks]
        self.assertNotIn(t1["id"], ids)
        self.assertNotIn(t2["id"], ids)

    def test_bulk_pause(self):
        t1 = self.create_task("c")
        t2 = self.create_task("d")

        r = client.post("/tasks/bulk/pause", json=[t1["id"], t2["id"]])
        self.assertEqual(r.status_code, 200)

        r = client.get("/tasks")
        tasks = r.json()
        filt = {t["id"]: t for t in tasks}
        self.assertEqual(filt[t1["id"]]["status"], "PAUSED")
        self.assertEqual(filt[t2["id"]]["status"], "PAUSED")

    def test_bulk_force_run(self):
        t1 = self.create_task("e")
        t2 = self.create_task("f")

        r = client.post("/tasks/bulk/force_run", json=[t1["id"], t2["id"]])
        self.assertEqual(r.status_code, 200)

        r = client.get("/tasks")
        tasks = r.json()
        filt = {t["id"]: t for t in tasks}
        self.assertIsNotNone(filt[t1["id"]].get("force_run_at"))
        self.assertIsNotNone(filt[t2["id"]].get("force_run_at"))

if __name__ == '__main__':
    unittest.main()
