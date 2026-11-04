"""FD001 preparation, causal features, engine-held-out selection and evaluation."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import zipfile
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
ARTIFACTS = ROOT / "artifacts"
WINDOW = 30
SENSORS = [f"sensor_{i}" for i in range(1, 22)]
COLUMNS = ["engine_id", "cycle", "setting_1", "setting_2", "setting_3", *SENSORS]
SENSOR_INFO = [
    ("Fan inlet temperature", "°R"), ("LPC outlet temperature", "°R"),
    ("HPC outlet temperature", "°R"), ("LPT outlet temperature", "°R"),
    ("Fan inlet pressure", "psia"), ("Bypass duct pressure", "psia"),
    ("HPC outlet total pressure", "psia"), ("Physical fan speed", "rpm"),
    ("Physical core speed", "rpm"), ("Engine pressure ratio", "ratio"),
    ("HPC outlet static pressure", "psia"), ("Fuel flow / Ps30", "pps/psi"),
    ("Corrected fan speed", "rpm"), ("Corrected core speed", "rpm"),
    ("Bypass ratio", "ratio"), ("Burner fuel-air ratio", "ratio"),
    ("Bleed enthalpy", "dataset units"), ("Demanded fan speed", "rpm"),
    ("Demanded corrected fan speed", "%"), ("HPT coolant bleed", "lbm/s"),
    ("LPT coolant bleed", "lbm/s"),
]


def read_data(path):
    frame = pd.read_csv(path, sep=r"\s+", header=None)
    if frame.shape[1] != 26 or not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError(f"{path}: expected 26 finite numeric fields per row")
    frame.columns = COLUMNS
    for col in ["engine_id", "cycle"]:
        if ((frame[col] < 1) | (frame[col] % 1 != 0)).any():
            raise ValueError(f"{path}: invalid {col}")
        frame[col] = frame[col].astype(int)
    if frame.duplicated(["engine_id", "cycle"]).any():
        raise ValueError(f"{path}: duplicate engine/cycle")
    for _, group in frame.groupby("engine_id", sort=False):
        if not np.array_equal(group.cycle, np.arange(1, len(group) + 1)):
            raise ValueError(f"{path}: cycles must start at 1 and be contiguous and ordered")
    return frame.reset_index(drop=True)


def features(frame, sensors):
    """Only the current and previous 29 observations, never another engine."""
    parts = []
    x = np.arange(WINDOW, dtype=float) - (WINDOW - 1) / 2
    denominator = float(x @ x)
    for _, group in frame.groupby("engine_id", sort=False):
        values = group[sensors]
        rolling = values.rolling(WINDOW, min_periods=WINDOW)
        part = pd.concat([
            values.add_suffix("_last"), rolling.mean().add_suffix("_mean"),
            rolling.std(ddof=0).add_suffix("_std"),
            rolling.apply(lambda y: float(y @ x) / denominator, raw=True).add_suffix("_slope"),
        ], axis=1)
        contiguous = group.cycle.diff().eq(1).rolling(WINDOW - 1).sum().eq(WINDOW - 1)
        part.loc[~contiguous] = np.nan
        parts.append(part)
    return pd.concat(parts).sort_index().dropna() if parts else pd.DataFrame()


def score(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    error = predicted - actual
    near, alert = actual <= 30, predicted <= 30
    return {
        "count": len(actual), "mae": float(np.abs(error).mean()),
        "rmse": float(np.sqrt((error ** 2).mean())), "mean_signed_error": float(error.mean()),
        "near_failure_count": int(near.sum()),
        "near_failure_mae": float(np.abs(error[near]).mean()) if near.any() else None,
        "alert_count": int(alert.sum()),
        "alert_precision": float((near & alert).sum() / alert.sum()) if alert.any() else None,
        "alert_recall": float((near & alert).sum() / near.sum()) if near.any() else None,
    }


def train(zip_path):
    RAW.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(exist_ok=True)
    # Exact known members only: no arbitrary archive paths are extracted.
    with zipfile.ZipFile(zip_path) as archive:
        for name in ["train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt", "readme.txt"]:
            (RAW / name).write_bytes(archive.read(name))
    frame = read_data(RAW / "train_FD001.txt")
    test = read_data(RAW / "test_FD001.txt")
    truth = np.loadtxt(RAW / "RUL_FD001.txt", dtype=float).reshape(-1)
    if (len(frame), frame.engine_id.nunique(), len(test), test.engine_id.nunique(), len(truth)) != (20631, 100, 13096, 100, 100):
        raise ValueError("Unexpected FD001 counts")
    if not np.isfinite(truth).all() or (truth < 0).any():
        raise ValueError("Invalid RUL targets")
    if sorted(test.engine_id.unique()) != list(range(1, 101)):
        raise ValueError("Test targets require engine IDs 1 through 100")
    target = frame.groupby("engine_id").cycle.transform("max") - frame.cycle
    fit_rows, val_rows = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=42).split(frame, groups=frame.engine_id))
    fit_ids = sorted(frame.iloc[fit_rows].engine_id.unique().tolist())
    val_ids = sorted(frame.iloc[val_rows].engine_id.unique().tolist())
    fit = frame[frame.engine_id.isin(fit_ids)]
    sensors = [s for s in SENSORS if fit[s].nunique() > 1]
    X = features(frame, sensors)
    train_index = X.index[frame.loc[X.index, "engine_id"].isin(fit_ids)]
    rng = np.random.default_rng(42)
    validation_index = []
    for engine in val_ids:
        group = frame[frame.engine_id == engine]
        eligible = group[(group.cycle >= WINDOW) & (group.cycle < group.cycle.max())]
        validation_index.extend(rng.choice(eligible.index, 5, replace=False).tolist())
    validation_index = sorted(validation_index)
    weights = 1 / frame.loc[train_index].groupby("engine_id").engine_id.transform("size")
    weights = weights / weights.mean()
    baseline = float(target.loc[train_index].median())
    validation_baseline = score(target.loc[validation_index], np.full(len(validation_index), baseline))
    candidates = []
    for depth, leaf in [(15, 5), (None, 3)]:
        model = RandomForestRegressor(n_estimators=250, max_depth=depth, min_samples_leaf=leaf, random_state=42, n_jobs=4)
        model.fit(X.loc[train_index], target.loc[train_index], sample_weight=weights)
        predicted = model.predict(X.loc[validation_index])
        metrics = score(target.loc[validation_index], predicted)
        candidates.append({"max_depth": depth, "min_samples_leaf": leaf, "metrics": metrics})
        print(f"Validation depth={depth}, leaf={leaf}: MAE={metrics['mae']:.3f}, RMSE={metrics['rmse']:.3f}", flush=True)
    winner = min(candidates, key=lambda c: c["metrics"]["mae"])
    sensors = [s for s in SENSORS if frame[s].nunique() > 1]
    X = features(frame, sensors)
    weights = 1 / frame.loc[X.index].groupby("engine_id").engine_id.transform("size")
    model = RandomForestRegressor(n_estimators=250, max_depth=winner["max_depth"], min_samples_leaf=winner["min_samples_leaf"], random_state=42, n_jobs=4)
    model.fit(X, target.loc[X.index], sample_weight=weights / weights.mean())
    Xt = features(test, sensors)
    all_predictions = model.predict(Xt)
    history = test.loc[Xt.index, ["engine_id", "cycle"]].copy()
    history["predicted_rul"] = all_predictions
    history.to_csv(ARTIFACTS / "test_history_predictions.csv", index=False)
    endpoints = history.groupby("engine_id", sort=True).tail(1).sort_values("engine_id").copy()
    endpoints["actual_rul"] = truth
    endpoints["error"] = endpoints.predicted_rul - endpoints.actual_rul
    endpoints.to_csv(ARTIFACTS / "test_predictions.csv", index=False)
    final_baseline = float(target.loc[X.index].median())
    metrics = {
        "test": score(truth, endpoints.predicted_rul),
        "baseline_test": score(truth, np.full(100, final_baseline)),
        "validation": winner["metrics"], "baseline_validation": validation_baseline,
        "candidates": candidates,
        "evaluation": "Official FD001 test: one final observation per engine, 100 engines. Uncapped RUL in cycles. Test used only after selection.",
        "validation_protocol": "80/20 engine split; five seeded pre-failure cutoffs per validation engine; equal observations per engine.",
    }
    version = "fd001-rf-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    metadata = {
        "version": version, "created_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": "Random Forest regression", "window": WINDOW, "target": "Uncapped remaining operational cycles",
        "sensors": sensors, "constant_sensors": [s for s in SENSORS if s not in sensors],
        "feature_names": list(X.columns), "feature_statistics": ["last", "mean", "population std", "linear slope"],
        "hyperparameters": {"trees": 250, "max_depth": winner["max_depth"], "min_samples_leaf": winner["min_samples_leaf"], "seed": 42},
        "fit_engine_ids": fit_ids, "validation_engine_ids": val_ids,
        "training_rows": len(frame), "training_windows": len(X), "test_rows": len(test),
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in RAW.glob("*.txt")},
        "versions": {"scikit_learn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
        "feature_importances": sorted([{"feature": f, "importance": float(v)} for f, v in zip(X.columns, model.feature_importances_)], key=lambda a: -a["importance"]),
    }
    joblib.dump({"model": model, "metadata": metadata}, ARTIFACTS / "model.joblib", compress=3)
    reloaded = joblib.load(ARTIFACTS / "model.joblib")
    np.testing.assert_allclose(reloaded["model"].predict(Xt.iloc[:10]), all_predictions[:10], atol=1e-8)
    for name, data in [("model_metadata.json", metadata), ("metrics.json", metrics)]:
        (ARTIFACTS / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    train(parser.parse_args().zip)

