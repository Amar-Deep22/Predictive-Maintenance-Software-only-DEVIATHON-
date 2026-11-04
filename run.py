"""Serve the built React portal and FD001 API on one local origin."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent

# Install-and-Run.cmd provisions the project environment. Re-enter it when the
# launcher is invoked with a global Python so dependencies are loaded together.
venv_python = root / ".venv" / "Scripts" / "python.exe"
if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
    os.execv(str(venv_python), [str(venv_python), str(Path(__file__).resolve()), *sys.argv[1:]])

import uvicorn
if not (root / "dist/index.html").exists():
    raise SystemExit("Build the UI first: npm run build")
sys.path.insert(0, str(root / "backend"))
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8767")))
