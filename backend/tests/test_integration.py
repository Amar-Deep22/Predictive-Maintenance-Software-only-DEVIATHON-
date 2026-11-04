import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app

HEADERS = {"X-Meridian-Client": "portal"}
class IntegrationChecks(unittest.TestCase):
    def test_disk_orders_and_production_assets(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / "data") as d:
            db = Path(d) / "orders.sqlite3"
            order = {"id":"WO-QA-001", "machine":"MOTOR-01", "name":"QA motor", "condition":"Critical", "priority":"Urgent inspection", "time":1, "params":{"rpm":1800,"temperature":110,"vibration":1.5,"current":6,"load":40}, "anomalies":[]}
            with TestClient(create_app(db)) as c:
                self.assertIn('/assets/', c.get('/').text)
                import re
                asset = re.search(r'src="([^"]+\.js)"', c.get('/').text).group(1)
                self.assertEqual(c.get(asset).status_code,200)
                self.assertEqual(c.post('/api/simulation-orders',json=order).status_code,403)
                self.assertEqual(c.post('/api/simulation-orders',headers=HEADERS,json=order).status_code,200)
                self.assertEqual(c.post('/api/simulation-orders',headers=HEADERS,json=order).status_code,200)
                self.assertEqual(c.post('/api/simulation-orders',headers=HEADERS,json={**order,'name':'changed'}).status_code,409)
                self.assertEqual(c.post('/api/simulation-orders',headers=HEADERS,json={**order,'params':{**order['params'],'rpm':-1}}).status_code,422)
                fleet=c.get('/api/machines').json()
                self.assertEqual(len(fleet[:5]),5)
                self.assertTrue(all(fleet[i]['rul']<=fleet[i+1]['rul'] for i in range(4)))
                saved=c.post('/api/work-orders',headers=HEADERS,json={'machine_id':fleet[0]['id']}).json()
                endpoint='/api/work-orders/'+saved['id']
                for status in ['Approved','In progress','Completed']:
                    self.assertEqual(c.patch(endpoint,headers=HEADERS,json={'status':status,'assignee':'QA engineer','notes':'Persistence test'}).status_code,200)
                self.assertEqual(c.patch(endpoint,headers=HEADERS,json={'status':'Draft'}).status_code,409)
                self.assertEqual(len(c.get('/api/model/predictions.csv').text.strip().splitlines()),101)
            with TestClient(create_app(db)) as c:
                self.assertEqual(c.get('/api/simulation-orders').json(),[order])
                self.assertEqual(c.get('/api/work-orders').json()[0]['status'],'Completed')
                self.assertEqual(c.get('/api/work-orders').json()[0]['assignee'],'QA engineer')
if __name__ == '__main__': unittest.main()
