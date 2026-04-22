"""
Backward-compat entry point — delegates to live_engine/main.py.

All launch scripts, systemd services, pgrep/pkill calls, and the
dashboard Popen call target this file so process names stay stable.
The actual bot logic lives in live_engine/main.py.
"""
import runpy
import sys
from pathlib import Path

# Keep project root in sys.path for any top-level import that happens
# before live_engine/main.py's own sys.path guard runs.
_root = str(Path(__file__).parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

runpy.run_path(
    str(Path(__file__).parent / "live_engine" / "main.py"),
    run_name="__main__",
)
