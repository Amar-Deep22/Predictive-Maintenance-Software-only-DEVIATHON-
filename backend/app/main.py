"""Local FD001 API. Start with python -m uvicorn app.main:app --host 127.0.0.1 --port 8765."""
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Literal
import uuid

import joblib
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ml import ROOT, RAW, ARTIFACTS, COLUMNS, SENSORS, SENSOR_INFO, WINDOW, features, read_data

from telegram_alerts import notify, init_workflow, start_listener
from work_orders import ensure_order

COMPONENT = {
    "component": "High-pressure compressor",
    "basis": "FD001 simulated HPC degradation scenario",
    "method": "dataset_prior",
    "model_diagnosed": False,
    "explanation": "FD001 models HPC degradation. This inspection focus comes from dataset context, not a learned component diagnosis.",
}
STATUSES = {
    "Draft": {"Approved", "Cancelled"},
    "Approved": {"In progress", "Cancelled"},
    "In progress": {"Completed", "Cancelled"},
    "Completed": set(), "Cancelled": set(),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def priority(rul):
    if rul is None:
        return "Pending", None
    band = "Critical" if rul <= 15 else "High" if rul <= 30 else "Medium" if rul <= 60 else "Low"
    return band, round(100 * max(0, min(1, (60 - rul) / 60)), 1)


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Reading(StrictBody):
    machine_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9:_-]+$")
    cycle: int = Field(strict=True, ge=1, le=100000)
    settings: list[FiniteFloat] = Field(min_length=3, max_length=3)
    sensors: list[FiniteFloat] = Field(min_length=21, max_length=21)


class ReplayStart(StrictBody):
    engine_id: int = Field(strict=True, ge=1, le=100)


class ReplayStep(StrictBody):
    count: int = Field(default=10, strict=True, ge=1, le=30)


class OrderCreate(StrictBody):
    machine_id: str = Field(min_length=1, max_length=80)


class OrderUpdate(StrictBody):
    expected_updated_at: str | None = Field(default=None, max_length=80)
    assignee: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=3000)
    status: Literal["Draft", "Approved", "In progress", "Completed", "Cancelled"]


class SimulationAnomaly(StrictBody):
    parameter: str = Field(max_length=80)
    value: FiniteFloat
    unit: str = Field(max_length=30)
    threshold: FiniteFloat
    severity: Literal["Normal", "Warning", "Critical"]
    action: str = Field(max_length=500)

class SimulationParams(StrictBody):
    rpm: FiniteFloat = Field(ge=0, le=5000)
    temperature: FiniteFloat = Field(ge=20, le=150)
    vibration: FiniteFloat = Field(ge=0, le=15)
    current: FiniteFloat = Field(ge=0, le=25)
    load: FiniteFloat = Field(ge=0, le=100)

class SimulationOrder(StrictBody):
    id: str = Field(pattern=r"^WO-[A-Z0-9-]+$", max_length=80)
    machine: Literal["MOTOR-01", "MOTOR-02", "MOTOR-03"]
    name: str = Field(max_length=100)
    condition: Literal["Normal", "Warning", "Critical"]
    priority: str = Field(max_length=100)
    time: FiniteFloat = Field(ge=0)
    params: SimulationParams
    anomalies: list[SimulationAnomaly] = Field(max_length=4)


def create_app(db_path=None):
    database = Path(db_path) if db_path else ROOT / "data" / "portal.sqlite3"

    @contextmanager
    def db():
        connection = sqlite3.connect(database, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def machine_record(c, machine_id):
        row = c.execute("""SELECT m.*, p.rul, p.priority, p.score, p.model_version
            FROM machines m LEFT JOIN predictions p ON p.machine_id=m.id AND p.cycle=m.last_cycle
            WHERE m.id=?""", (machine_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Machine not found")
        result = dict(row)
        result["name"] = f"Machine {result['source_engine']:02d}"
        result["component"] = COMPONENT
        result["data_status"] = (
            "Recorded history complete" if result["source"] == "test" or result["complete"]
            else f"Collecting history: {result['last_cycle']}/{WINDOW} cycles" if result["last_cycle"] < WINDOW
            else "Replay paused / ready to advance"
        )
        return result

    def insert_reading(c, body):
        machine = c.execute("SELECT * FROM machines WHERE id=?", (body.machine_id,)).fetchone()
        if machine is None:
            raise HTTPException(404, "Start a replay session before ingesting readings")
        payload = json.dumps([*body.settings, *body.sensors])
        existing = c.execute("SELECT values_json FROM readings WHERE machine_id=? AND cycle=?",
                             (body.machine_id, body.cycle)).fetchone()
        if existing:
            if json.loads(existing[0]) != json.loads(payload):
                raise HTTPException(409, "Conflicting reading already exists for this cycle")
            return
        if machine["source"] != "replay":
            raise HTTPException(409, "The reference fleet is read-only; create a replay session")
        if machine["complete"]:
            raise HTTPException(409, "Recorded history is complete")
        if body.cycle != machine["last_cycle"] + 1:
            raise HTTPException(409, "Readings must arrive in consecutive cycle order")
        # Verify replay content: this model is not a generic live-hardware model.
        reference = app.state.test[app.state.test.engine_id == machine["source_engine"]]
        expected = reference[reference.cycle == body.cycle]
        if expected.empty or list(expected.iloc[0, 2:].astype(float)) != [*body.settings, *body.sensors]:
            raise HTTPException(422, "Reading must match the selected FD001 replay engine and cycle")
        c.execute("INSERT INTO readings VALUES(?,?,?)", (body.machine_id, body.cycle, payload))
        c.execute("UPDATE machines SET last_cycle=?, updated_at=?, complete=? WHERE id=?",
                  (body.cycle, now(), int(body.cycle == int(reference.cycle.max())), body.machine_id))
        if body.cycle >= WINDOW:
            rows = c.execute("SELECT cycle,values_json FROM readings WHERE machine_id=? ORDER BY cycle DESC LIMIT ?",
                             (body.machine_id, WINDOW)).fetchall()[::-1]
            frame = pd.DataFrame([[machine["source_engine"], r["cycle"], *json.loads(r["values_json"])] for r in rows], columns=COLUMNS)
            X = features(frame, app.state.metadata["sensors"])
            if X.empty:
                raise HTTPException(422, "A complete 30-cycle window is required")
            rul = max(0.0, float(app.state.model.predict(X[app.state.metadata["feature_names"]])[-1]))
            band, risk_score = priority(rul)
            c.execute("INSERT INTO predictions VALUES(?,?,?,?,?,?)",
                      (body.machine_id, body.cycle, rul, band, risk_score, app.state.metadata["version"]))

    @asynccontextmanager
    async def lifespan(application):
        if not (ARTIFACTS / "model.joblib").exists():
            raise RuntimeError("Train first: python ml.py --zip PATH_TO_CMAPSSData.zip")
        bundle = joblib.load(ARTIFACTS / "model.joblib")  # Trusted, locally trained artifact only.
        application.state.model = bundle["model"]
        application.state.model.n_jobs = 1
        application.state.metadata = bundle["metadata"]
        application.state.test = read_data(RAW / "test_FD001.txt")
        database.parent.mkdir(parents=True, exist_ok=True)
        with db() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS simulation_orders(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS machines(
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, source TEXT NOT NULL,
                    source_engine INTEGER NOT NULL, last_cycle INTEGER NOT NULL DEFAULT 0,
                    complete INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS readings(
                    machine_id TEXT NOT NULL REFERENCES machines(id), cycle INTEGER NOT NULL,
                    values_json TEXT NOT NULL, PRIMARY KEY(machine_id,cycle));
                CREATE TABLE IF NOT EXISTS predictions(
                    machine_id TEXT NOT NULL REFERENCES machines(id), cycle INTEGER NOT NULL,
                    rul REAL NOT NULL, priority TEXT NOT NULL, score REAL NOT NULL,
                    model_version TEXT NOT NULL, PRIMARY KEY(machine_id,cycle));
                CREATE TABLE IF NOT EXISTS work_orders(
                    id TEXT PRIMARY KEY, machine_id TEXT NOT NULL REFERENCES machines(id),
                    cycle INTEGER NOT NULL, rul REAL NOT NULL, priority TEXT NOT NULL,
                    model_version TEXT NOT NULL, component TEXT NOT NULL, basis TEXT NOT NULL,
                    instructions TEXT NOT NULL, assignee TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Draft',
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    UNIQUE(machine_id,cycle,model_version));
            """)
            stored = c.execute("SELECT value FROM settings WHERE key='model_version'").fetchone()
            if stored and stored[0] != bundle["metadata"]["version"]:
                raise RuntimeError("Model version changed. Back up data/portal.sqlite3 and use a new database; existing work orders must be preserved.")
            if not stored:
                c.execute("INSERT INTO settings VALUES('model_version',?)", (bundle["metadata"]["version"],))
                for engine, group in application.state.test.groupby("engine_id"):
                    machine_id = f"FD001:test:{int(engine):03d}"
                    c.execute("INSERT INTO machines VALUES(?,?,?,?,?,?,?)",
                              (machine_id, f"Machine {int(engine):02d}", "test", int(engine), int(group.cycle.max()), 1, now()))
                    c.executemany("INSERT INTO readings VALUES(?,?,?)",
                                  [(machine_id, int(row[1]), json.dumps(list(map(float, row[2:])))) for row in group.itertuples(index=False, name=None)])
                history = pd.read_csv(ARTIFACTS / "test_history_predictions.csv")
                for row in history.itertuples(index=False):
                    band, risk_score = priority(row.predicted_rul)
                    c.execute("INSERT INTO predictions VALUES(?,?,?,?,?,?)",
                              (f"FD001:test:{int(row.engine_id):03d}", int(row.cycle), row.predicted_rul, band, risk_score, bundle["metadata"]["version"]))
        with db() as c:
            init_workflow(c)
        stop_listener = start_listener(database) if db_path is None else lambda: None
        try:
            yield
        finally:
            stop_listener()

    app = FastAPI(title="Anuraksana · FD001 Maintenance", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def local_security(request: Request, call_next):
        if request.method in {"POST", "PATCH", "PUT", "DELETE"}:
            if request.headers.get("x-meridian-client") != "portal":
                return JSONResponse({"detail": "Missing local client header"}, status_code=403)
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Cross-origin writes are not allowed"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path == "/":
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    @app.get("/api/simulation-orders")
    def simulation_orders():
        with db() as c:
            return [json.loads(r[0]) for r in c.execute("SELECT payload FROM simulation_orders ORDER BY rowid DESC")]

    @app.post("/api/simulation-orders")
    def save_simulation_order(body: SimulationOrder):
        payload = body.model_dump_json()
        with db() as c:
            c.execute("BEGIN IMMEDIATE")
            existing = c.execute("SELECT payload FROM simulation_orders WHERE id=?", (body.id,)).fetchone()
            if existing and json.loads(existing[0]) != json.loads(payload):
                raise HTTPException(409, "Work order snapshot already exists")
            c.execute("INSERT OR IGNORE INTO simulation_orders VALUES(?,?)", (body.id, payload))
        return body

    @app.get("/api/health")
    def health():
        return {"status": "ready", "model_version": app.state.metadata["version"], "dataset": "FD001"}

    @app.get("/api/machines")
    def machines():
        with db() as c:
            ids = [row[0] for row in c.execute("SELECT id FROM machines")]
            results = [machine_record(c, machine_id) for machine_id in ids]
        return sorted(results, key=lambda item: (item["rul"] is None, item["rul"] or 0, item["id"]))

    @app.get("/api/machines/{machine_id}")
    def machine(machine_id: str):
        with db() as c:
            return machine_record(c, machine_id)

    @app.get("/api/machines/{machine_id}/history")
    def history(machine_id: str, sensor: int = Query(default=3, ge=1, le=21)):
        with db() as c:
            item = machine_record(c, machine_id)
            rows = c.execute("SELECT cycle,values_json FROM readings WHERE machine_id=? ORDER BY cycle", (machine_id,)).fetchall()
            predictions = [dict(r) for r in c.execute("SELECT cycle,rul FROM predictions WHERE machine_id=? ORDER BY cycle", (machine_id,))]
        series = [{"cycle": r["cycle"], "value": json.loads(r["values_json"])[sensor + 2]} for r in rows]
        observation = None
        if len(series) >= WINDOW:
            window = series[-WINDOW:]
            delta = window[-1]["value"] - window[0]["value"]
            observation = {"change": delta, "over_cycles": WINDOW - 1, "description": "Observed change only; it does not establish a failing component."}
        return {"machine": item, "sensor": sensor, "label": SENSOR_INFO[sensor - 1][0],
                "unit": SENSOR_INFO[sensor - 1][1], "series": series, "predictions": predictions, "observation": observation}

    @app.get("/api/sensors")
    def sensors():
        return [{"id": i + 1, "label": label, "unit": unit, "used_by_model": f"sensor_{i + 1}" in app.state.metadata["sensors"]}
                for i, (label, unit) in enumerate(SENSOR_INFO)]

    @app.get("/api/model/metrics")
    def metrics():
        data = json.loads((ARTIFACTS / "metrics.json").read_text(encoding="utf-8"))
        data["metadata"] = app.state.metadata
        data["predictions"] = pd.read_csv(ARTIFACTS / "test_predictions.csv").to_dict(orient="records")
        return data

    @app.get("/api/model/predictions.csv")
    def prediction_download():
        return FileResponse(ARTIFACTS / "test_predictions.csv", filename="fd001-test-predictions.csv", media_type="text/csv")

    @app.post("/api/readings")
    def ingest(body: Reading, background_tasks: BackgroundTasks):
        with db() as c:
            c.execute("BEGIN IMMEDIATE")
            insert_reading(c, body)
            result = machine_record(c, body.machine_id)
        background_tasks.add_task(notify, database, result)
        return result

    @app.post("/api/replay/start")
    def start_replay(body: ReplayStart):
        machine_id = f"FD001:replay:{body.engine_id:03d}:{uuid.uuid4().hex[:8]}"
        with db() as c:
            c.execute("INSERT INTO machines VALUES(?,?,?,?,?,?,?)",
                      (machine_id, f"Machine {body.engine_id:02d}", "replay", body.engine_id, 0, 0, now()))
            return machine_record(c, machine_id)

    @app.post("/api/replay/{machine_id}/step")
    def step_replay(machine_id: str, body: ReplayStep, background_tasks: BackgroundTasks):
        with db() as c:
            c.execute("BEGIN IMMEDIATE")
            item = machine_record(c, machine_id)
            if item["source"] != "replay":
                raise HTTPException(409, "Only replay sessions can advance")
            future = app.state.test[(app.state.test.engine_id == item["source_engine"]) &
                                    (app.state.test.cycle > item["last_cycle"])].head(body.count)
            for row in future.itertuples(index=False, name=None):
                insert_reading(c, Reading(machine_id=machine_id, cycle=int(row[1]), settings=list(row[2:5]), sensors=list(row[5:])))
            result = machine_record(c, machine_id)
        background_tasks.add_task(notify, database, result)
        return result

    @app.get("/api/work-orders")
    def orders():
        with db() as c:
            result=[dict(r) for r in c.execute("SELECT * FROM work_orders ORDER BY created_at DESC")]
            for order in result:
                order["responses"]=[dict(r) for r in c.execute("SELECT worker,action,created_at FROM worker_responses WHERE order_id=? ORDER BY created_at",(order["id"],))]
            return result

    @app.post("/api/work-orders")
    def create_order(body: OrderCreate):
        with db() as c:
            c.execute("BEGIN IMMEDIATE")
            item = machine_record(c, body.machine_id)
            if item["rul"] is None:
                raise HTTPException(409, "Collect 30 cycles before creating a prediction-linked draft")
            return ensure_order(c, item)

    @app.patch("/api/work-orders/{order_id}")
    def update_order(order_id: str, body: OrderUpdate):
        with db() as c:
            c.execute("BEGIN IMMEDIATE")
            old = c.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone()
            if old is None:
                raise HTTPException(404, "Work order not found")
            if body.expected_updated_at is not None and body.expected_updated_at != old["updated_at"]:
                raise HTTPException(409, "This order changed. Refresh work orders before saving again.")
            if body.status != old["status"] and body.status not in STATUSES[old["status"]]:
                raise HTTPException(409, f"Cannot move from {old['status']} to {body.status}")
            c.execute("UPDATE work_orders SET assignee=?,notes=?,status=?,updated_at=? WHERE id=?",
                      (body.assignee.strip(), body.notes.strip(), body.status, now(), order_id))
            return dict(c.execute("SELECT * FROM work_orders WHERE id=?", (order_id,)).fetchone())

    @app.get("/")
    def index():
        return FileResponse(ROOT.parent / "dist" / "index.html")

    app.mount("/assets", StaticFiles(directory=ROOT.parent / "dist" / "assets", check_dir=False), name="assets")
    return app


app = create_app()

