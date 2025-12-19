import unittest
from fastapi.testclient import TestClient
from api.main import app


class TestCronPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_api_cron_next_valid(self):
        resp = self.client.get('/api/cron/next?cron=*/5 * * * *&n=3')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('next_runs', data)
        self.assertEqual(len(data['next_runs']), 3)

    def test_api_cron_next_invalid_cron(self):
        resp = self.client.get('/api/cron/next?cron=invalidcron')
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('error', data)

    def test_task_detail_shows_next_runs(self):
        resp = self.client.post('/tasks', json={"name": "t1", "cron": "*/10 * * * *", "command": "echo hi"})
        self.assertEqual(resp.status_code, 200)
        task = resp.json()
        task_id = task['id']

        ui = self.client.get(f'/ui/tasks/{task_id}')
        self.assertEqual(ui.status_code, 200)
        text = ui.text
        self.assertIn('下次运行', text)


if __name__ == '__main__':
    unittest.main()
