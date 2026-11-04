"""Shared creation path for portal and Telegram prediction-linked drafts."""
from datetime import datetime, timezone
import uuid

def ensure_order(c, item):
    existing=c.execute('SELECT * FROM work_orders WHERE machine_id=? AND cycle=? AND model_version=?',
        (item['id'],item['last_cycle'],item['model_version'])).fetchone()
    if existing: return dict(existing)
    stamp=datetime.now(timezone.utc).isoformat()
    oid='WO-'+uuid.uuid4().hex[:8].upper()
    instructions=(f"Review sensor trends for {item['name']} at cycle {item['last_cycle']}. "
        f"Estimated remaining life: {item['rul']:.1f} operating cycles. "
        "Arrange an HPC inspection using the applicable maintenance procedure. "
        "HPC is the known FD001 scenario, not an independently diagnosed fault. "
        "Engineer approval is required before inspection; cycles are not calendar deadlines.")
    c.execute('''INSERT INTO work_orders(id,machine_id,cycle,rul,priority,model_version,component,basis,instructions,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(oid,item['id'],item['last_cycle'],item['rul'],item['priority'],item['model_version'],
        'High-pressure compressor','FD001 simulated HPC degradation scenario',instructions,stamp,stamp))
    return dict(c.execute('SELECT * FROM work_orders WHERE id=?',(oid,)).fetchone())
