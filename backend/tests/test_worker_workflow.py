from contextlib import closing
import sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from telegram_alerts import init_workflow,handle_callback,notify
from work_orders import ensure_order

class WorkflowChecks(unittest.TestCase):
 def test_notify_and_worker_lifecycle(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'test.sqlite3'
   with closing(sqlite3.connect(path)) as db, db:
    db.row_factory=sqlite3.Row
    db.execute('''CREATE TABLE work_orders(id TEXT PRIMARY KEY,machine_id TEXT,cycle INTEGER,rul REAL,priority TEXT,model_version TEXT,component TEXT,basis TEXT,instructions TEXT,assignee TEXT DEFAULT '',notes TEXT DEFAULT '',status TEXT DEFAULT 'Draft',created_at TEXT,updated_at TEXT,UNIQUE(machine_id,cycle,model_version))''')
    init_workflow(db)
   workers=[{'worker_id':f'WORKER-0{i}','chat_id':str(i)} for i in range(1,4)]
   item={'id':'FD001:replay:034:test','name':'Machine 34','last_cycle':203,'rul':6.9,'priority':'Critical','model_version':'test'}
   config={'enabled':True,'bot_token':'test-token','workers':workers}
   with patch('telegram_alerts.configuration',return_value=config),patch('telegram_alerts.telegram',return_value={'message_id':1}) as send:
    notify(path,item);notify(path,item)
    self.assertEqual(send.call_count,3)
    payload=send.call_args.args[2];self.assertIn('reply_markup',payload)
    oid=payload['reply_markup']['inline_keyboard'][0][0]['callback_data'].split(':')[1]
   def query(action='ack',sender=1):return {'from':{'id':sender},'message':{'chat':{'id':sender,'type':'private'}},'data':f'{action}:{oid}'}
   self.assertIn('restricted',handle_callback(path,query(sender=99),workers))
   self.assertIn('approve',handle_callback(path,query('start'),workers))
   self.assertIn('acknowledgement recorded',handle_callback(path,query(),workers))
   self.assertIn('already recorded',handle_callback(path,query(),workers))
   with closing(sqlite3.connect(path)) as db, db:
    self.assertEqual(db.execute('SELECT status FROM work_orders').fetchone()[0],'Draft')
    db.execute("UPDATE work_orders SET status='Approved'")
   self.assertIn('inspection started',handle_callback(path,query('start'),workers))
   with closing(sqlite3.connect(path)) as db, db:
    self.assertEqual(db.execute('SELECT status,assignee FROM work_orders').fetchone(),('In progress','WORKER-01'))
    self.assertEqual(db.execute('SELECT COUNT(*) FROM worker_responses').fetchone()[0],2)
   self.assertIn('already recorded',handle_callback(path,query('start'),workers))
   with closing(sqlite3.connect(path)) as db, db:db.execute("UPDATE work_orders SET status='Completed'")
   self.assertIn('closed',handle_callback(path,query(sender=2),workers))

if __name__=='__main__':unittest.main()
