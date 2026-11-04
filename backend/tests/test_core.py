"""Focused regression checks. Run: python -m unittest discover -s tests -v."""
import json
from pathlib import Path
import tempfile
import unittest
import joblib
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from ml import RAW, ARTIFACTS, WINDOW, SENSORS, COLUMNS, features, read_data
from app.main import create_app, priority

HEADERS = {"X-Meridian-Client": "portal"}


class CoreChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = read_data(RAW / "test_FD001.txt")
        cls.bundle = joblib.load(ARTIFACTS / "model.joblib")
        cls.bundle["model"].n_jobs = 1

    def test_feature_causality_boundaries_and_gaps(self):
        frame = self.raw[self.raw.engine_id <= 2]
        engine = frame[frame.engine_id == 1].reset_index(drop=True)
        sensors = self.bundle["metadata"]["sensors"]
        before = features(engine.iloc[:30], sensors)
        after = features(engine, sensors)
        np.testing.assert_allclose(before.iloc[0], after.iloc[0], atol=1e-8)
        self.assertTrue(features(engine.iloc[:29], sensors).empty)
        combined = features(frame, sensors)
        self.assertTrue((frame.loc[combined.index, "cycle"] >= 30).all())
        second = frame[frame.engine_id == 2]
        independent = features(second, sensors)
        np.testing.assert_allclose(combined.loc[independent.index], independent)
        gapped = engine.iloc[:30].copy()
        gapped.loc[gapped.index[-1], "cycle"] += 1
        self.assertTrue(features(gapped, sensors).empty)
        # A sensor that increases one unit per cycle has a slope of one.
        ramp = engine.iloc[:30].copy()
        ramp["sensor_2"] = np.arange(30)
        self.assertAlmostEqual(features(ramp, ["sensor_2"]).iloc[0]["sensor_2_slope"], 1)

    def test_split_and_artifact_predictions(self):
        meta = self.bundle["metadata"]
        self.assertFalse(set(meta["fit_engine_ids"]) & set(meta["validation_engine_ids"]))
        self.assertEqual(len(meta["fit_engine_ids"]), 80)
        self.assertEqual(len(meta["validation_engine_ids"]), 20)
        self.assertNotIn("engine_id", meta["feature_names"])
        saved = pd.read_csv(ARTIFACTS / "test_predictions.csv")
        X = features(self.raw, meta["sensors"])
        endpoint_index = self.raw.groupby("engine_id").tail(1).index
        result = self.bundle["model"].predict(X.loc[endpoint_index])
        np.testing.assert_allclose(result, saved.predicted_rul, atol=1e-8)
        metrics = json.loads((ARTIFACTS / "metrics.json").read_text())
        self.assertAlmostEqual(float(np.abs(result - saved.actual_rul).mean()), metrics["test"]["mae"])
        self.assertLess(metrics["test"]["mae"], metrics["baseline_test"]["mae"])

    def test_priority_boundaries(self):
        for rul, band in [(None, "Pending"), (0, "Critical"), (15, "Critical"), (15.01, "High"),
                          (30, "High"), (30.01, "Medium"), (60, "Medium"), (60.01, "Low")]:
            self.assertEqual(priority(rul)[0], band)

    def test_portal_replay_orders_and_persistence(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / "data") as directory:
            path = Path(directory) / "test.sqlite3"
            with TestClient(create_app(path)) as client:
                self.assertEqual(client.get("/").status_code, 200)
                fleet = client.get("/api/machines").json()
                self.assertEqual(len(fleet), 100)
                self.assertEqual([m["rul"] for m in fleet], sorted(m["rul"] for m in fleet))
                self.assertFalse(fleet[0]["component"]["model_diagnosed"])
                self.assertNotIn("actual_rul", fleet[0])
                self.assertEqual(client.post("/api/replay/start", json={"engine_id":1}).status_code, 403)
                self.assertEqual(client.post("/api/replay/start", headers={**HEADERS,"Origin":"https://example.com"}, json={"engine_id":1}).status_code, 403)
                self.assertEqual(client.post("/api/replay/start", headers=HEADERS, json={"engine_id":101}).status_code, 422)
                m = client.post("/api/replay/start", headers=HEADERS, json={"engine_id":1}).json()
                mid = m["id"]
                self.assertIsNone(m["rul"])
                self.assertEqual(client.post("/api/work-orders", headers=HEADERS, json={"machine_id":mid}).status_code, 409)
                row = self.raw.iloc[0]
                body = {"machine_id":mid,"cycle":1,"settings":row.iloc[2:5].tolist(),"sensors":row.iloc[5:].tolist()}
                self.assertEqual(client.post("/api/readings", headers=HEADERS, json=body).status_code, 200)
                self.assertEqual(client.post("/api/readings", headers=HEADERS, json=body).status_code, 200)
                bad = {**body, "sensors":[0]*21}
                self.assertEqual(client.post("/api/readings", headers=HEADERS, json=bad).status_code, 409)
                self.assertEqual(client.post("/api/readings", headers=HEADERS, json={**body,"cycle":3}).status_code, 409)
                self.assertEqual(client.post("/api/readings", headers=HEADERS, json={**body,"sensors":[1]}).status_code, 422)
                self.assertEqual(client.post("/api/readings", headers=HEADERS, json={**body,"sensors":["NaN"]*21}).status_code, 422)
                self.assertEqual(client.post("/api/readings", headers=HEADERS, json={**body,"actual_rul":5}).status_code, 422)
                step = "/api/replay/" + mid + "/step"
                self.assertEqual(client.post(step, headers=HEADERS, json={"count":28}).json()["last_cycle"],29)
                m = client.post(step, headers=HEADERS, json={"count":1}).json()
                self.assertIsNotNone(m["rul"])
                expected = self.bundle["model"].predict(features(self.raw[self.raw.engine_id==1].iloc[:30],self.bundle["metadata"]["sensors"]))[0]
                self.assertAlmostEqual(m["rul"], expected)
                m = client.post(step, headers=HEADERS, json={"count":10}).json()
                self.assertEqual(m["last_cycle"],31)
                self.assertEqual(m["complete"],1)
                self.assertEqual(client.post(step, headers=HEADERS, json={"count":10}).json()["last_cycle"],31)
                first = client.post("/api/work-orders", headers=HEADERS, json={"machine_id":mid}).json()
                second = client.post("/api/work-orders", headers=HEADERS, json={"machine_id":mid}).json()
                self.assertEqual(first["id"],second["id"])
                endpoint = "/api/work-orders/" + first["id"]
                self.assertEqual(client.patch(endpoint, headers=HEADERS, json={"status":"Completed"}).status_code,409)
                updated = client.patch(endpoint, headers=HEADERS, json={"status":"Approved","assignee":"Test engineer","notes":"Review fixture"}).json()
                self.assertEqual(updated["status"],"Approved")
                self.assertEqual(updated["rul"],first["rul"])
                history = client.get("/api/machines/"+mid+"/history?sensor=3").json()
                self.assertEqual(len(history["series"]),31)
                self.assertEqual(len(history["predictions"]),2)
                self.assertNotIn("actual_rul",history)
                self.assertEqual(client.get("/api/machines/"+mid+"/history?sensor=22").status_code,422)
                self.assertEqual(client.get("/api/model/metrics").json()["test"]["count"],100)
            with TestClient(create_app(path)) as reopened:
                orders = reopened.get("/api/work-orders").json()
                self.assertEqual(len(orders),1)
                self.assertEqual(orders[0]["assignee"],"Test engineer")
                self.assertEqual(orders[0]["notes"],"Review fixture")


if __name__ == "__main__":
    unittest.main()

