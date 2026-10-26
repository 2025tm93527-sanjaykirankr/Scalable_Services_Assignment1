"""Run BR1-BR5 unit tests and record timestamped raw output."""
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def main():
    started = datetime.now(timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")).isoformat(timespec="seconds")
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_business_rules.py", "-v"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    finished = datetime.now(timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")).isoformat(timespec="seconds")
    content = (
        f"Timestamp (Asia/Kolkata): {finished}\nCommand: {' '.join(command)}\n"
        f"Started: {started}\nExit code: {result.returncode}\n\n"
        f"{result.stdout}{result.stderr}"
    )
    (OUT / "business-rule-tests.txt").write_text(content, encoding="utf-8")
    print(content, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
