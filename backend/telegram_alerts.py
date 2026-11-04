from contextlib import closing
"""Optional Telegram demo alerts. Secrets remain in a local ignored file."""
import json
from html import escape
import sqlite3
import threading
import urllib.request
from pathlib import Path
CONFIG = Path(__file__).parent / "telegram.local.json"
LOCK = threading.Lock()

def message(item):
    if item.get("rul") is None or item["rul"] > 30:
        return None
    return ("<b>ANURAKSANA DEMO ALERT</b> — recorded FD001 data\n\n"
            f"<b>Machine: {escape(str(item['name']))}</b>\n"
            f"Session: <code>{escape(str(item['id']))}</code>\n"
            f"<b>Priority: {escape(str(item['priority']))}</b> | Cycle: {escape(str(item['last_cycle']))}\n"
            f"<b>Predicted remaining life: {item['rul']:.1f} cycles</b>\n"
            "Model: <b>Random Forest — FD001 remaining-life model</b>\n\n"
            "<b>Reason:</b> Prediction is within the 30-cycle alert band.\n"
            "<b>Inspection focus: High-pressure compressor (HPC)</b>\n"
            "FD001 scenario assumption, not confirmed diagnosis.\n\n"
            "<b>Recommended action:</b> Request engineering review and inspect sensor trends/HPC using the applicable procedure.\n"
            "<b>Replacement: not established</b>; inspection must determine repair or replacement.\n\n"
            "Location: simulated FD001 machine; no physical plant location configured.\n"
            "<b>Cycles are not days.</b> This is not a live hardware alarm.")

def init_workflow(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS telegram_delivery(machine TEXT,chat TEXT,band TEXT,status TEXT,PRIMARY KEY(machine,chat,band));
        CREATE TABLE IF NOT EXISTS alert_orders(machine TEXT,band TEXT,order_id TEXT NOT NULL,PRIMARY KEY(machine,band));
        CREATE TABLE IF NOT EXISTS worker_responses(order_id TEXT,worker TEXT,action TEXT,created_at TEXT,PRIMARY KEY(order_id,worker,action));
        CREATE TABLE IF NOT EXISTS telegram_state(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    ''')

def configuration():
    try:
        c=json.loads(CONFIG.read_text(encoding='utf-8-sig'))
        workers=c.get('workers',[])
        if c.get('enabled') is not True or not c.get('bot_token') or len(workers)!=3: return None
        if any(not str(w.get('chat_id','')).isdigit() or not w.get('worker_id') for w in workers): return None
        if len({str(w['chat_id']) for w in workers})!=3 or len({w['worker_id'] for w in workers})!=3: return None
        return c
    except (OSError,ValueError,TypeError): return None

def telegram(token, method, payload):
    request=urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=20) as response:
            result=json.load(response)
        if not result.get('ok'): raise RuntimeError('Telegram request rejected')
        return result['result']
    except Exception:
        # Do not expose the URL: it contains the bot token.
        raise RuntimeError('Telegram request failed; check connectivity and bot configuration') from None

def notify(database, item):
    from work_orders import ensure_order
    with LOCK:
        config=configuration()
        text=message(item)
        if not config or text is None: return
        with closing(sqlite3.connect(database,timeout=20)) as db, db:
            db.row_factory=sqlite3.Row
            init_workflow(db)
            db.execute('BEGIN IMMEDIATE')
            linked=db.execute('SELECT order_id FROM alert_orders WHERE machine=? AND band=?',(item['id'],item['priority'])).fetchone()
            if linked: oid=linked[0]
            else:
                oid=ensure_order(db,item)['id']
                db.execute('INSERT INTO alert_orders VALUES(?,?,?)',(item['id'],item['priority'],oid))
            db.commit()
            text+=f'\n\n<b>Work order: {escape(oid)}</b>\nAcknowledge receipt below. Starting inspection requires portal approval.'
            buttons={'inline_keyboard':[[{'text':'Acknowledge','callback_data':f'ack:{oid}'},{'text':'Start inspection','callback_data':f'start:{oid}'}]]}
            for worker in config['workers']:
                chat=str(worker['chat_id']);key=(item['id'],chat,item['priority'])
                row=db.execute('SELECT status FROM telegram_delivery WHERE machine=? AND chat=? AND band=?',key).fetchone()
                if row and row[0]=='sent':continue
                status='failed'
                try:
                    telegram(config['bot_token'],'sendMessage',{'chat_id':chat,'text':text,'parse_mode':'HTML','reply_markup':buttons})
                    status='sent'
                except RuntimeError: pass
                db.execute('INSERT OR REPLACE INTO telegram_delivery VALUES(?,?,?,?)',(*key,status));db.commit()

def handle_callback(database, query, workers):
    from datetime import datetime, timezone
    sender=str(query.get('from',{}).get('id',''))
    chat=query.get('message',{}).get('chat',{})
    worker=next((w for w in workers if str(w['chat_id'])==sender),None)
    if not worker or str(chat.get('id'))!=sender or chat.get('type')!='private': return 'This action is restricted to the configured workers.'
    parts=str(query.get('data','')).split(':')
    if len(parts)!=2 or parts[0] not in ('ack','start'):return 'Unknown action.'
    action,oid=parts;actor=worker['worker_id'];stamp=datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(database,timeout=20)) as db, db:
        db.row_factory=sqlite3.Row
        db.execute('BEGIN IMMEDIATE')
        linked=db.execute('''SELECT 1 FROM alert_orders a JOIN telegram_delivery d ON d.machine=a.machine AND d.band=a.band
            WHERE a.order_id=? AND d.chat=? AND d.status='sent' ''',(oid,sender)).fetchone()
        if not linked:return 'No delivered alert is linked to this work order.'
        order=db.execute('SELECT * FROM work_orders WHERE id=?',(oid,)).fetchone()
        if not order:return 'Work order no longer available.'
        if order['status'] in ('Completed','Cancelled'):return 'This work order is already closed.'
        if db.execute('SELECT 1 FROM worker_responses WHERE order_id=? AND worker=? AND action=?',(oid,actor,action)).fetchone():return 'Your response is already recorded.'
        if action=='start':
            if order['status']!='Approved':return 'Ask the manager to approve this order in the portal before starting.'
            if order['assignee'] and order['assignee']!=actor:return 'This order is assigned to another worker. Ask the manager to update it.'
            db.execute("UPDATE work_orders SET assignee=?,status='In progress',updated_at=? WHERE id=?",(actor,stamp,oid))
        else:
            db.execute('UPDATE work_orders SET updated_at=? WHERE id=?',(stamp,oid))
        db.execute('INSERT INTO worker_responses VALUES(?,?,?,?)',(oid,actor,action,stamp))
    return f'{oid}: '+('acknowledgement recorded.' if action=='ack' else 'inspection started; you are assigned.')

def start_listener(database):
    """One local long-poll listener; no public webhook or exposed portal required."""
    import hashlib
    import logging
    stop=threading.Event()
    def run():
        # Lock the bot configuration path so two portal processes cannot consume the same updates.
        import os
        lockfile=CONFIG.with_suffix('.poll.lock')
        with open(lockfile,'a+b') as lease:
            lease.seek(0);lease.write(b'0');lease.flush();lease.seek(0)
            try:
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:
                logging.warning('Telegram listener already active in another portal process.');return
            while not stop.is_set():
                config=configuration()
                if not config:
                    stop.wait(5);continue
                key='offset:'+hashlib.sha256(config['bot_token'].encode()).hexdigest()[:16]
                try:
                    with closing(sqlite3.connect(database,timeout=20)) as db, db:
                        row=db.execute('SELECT value FROM telegram_state WHERE key=?',(key,)).fetchone()
                    updates=telegram(config['bot_token'],'getUpdates',{'offset':int(row[0]) if row else 0,'timeout':10,'allowed_updates':['callback_query']})
                    for update in updates:
                        query=update.get('callback_query')
                        if query:
                            answer=handle_callback(database,query,config['workers'])
                            try:telegram(config['bot_token'],'answerCallbackQuery',{'callback_query_id':query['id'],'text':answer[:200],'show_alert':True})
                            except RuntimeError:pass # Response remains committed; an expired popup must not replay a state change.
                        with closing(sqlite3.connect(database,timeout=20)) as db, db:
                            db.execute('INSERT OR REPLACE INTO telegram_state VALUES(?,?)',(key,str(update['update_id']+1)))
                except (RuntimeError,sqlite3.Error,KeyError,TypeError,ValueError):
                    logging.warning('Telegram listener could not process updates; retrying without changing work orders.')
                    stop.wait(5)
    thread=threading.Thread(target=run,name='telegram-responses',daemon=True);thread.start()
    def close():
        stop.set();thread.join(timeout=22)
    return close
