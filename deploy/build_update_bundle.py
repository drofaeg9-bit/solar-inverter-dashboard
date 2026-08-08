#!/usr/bin/env python3
"""Build the single-file Orange Pi dashboard update archive."""

from __future__ import annotations

import shutil
import subprocess
import sqlite3
import tempfile
import zipapp
from pathlib import Path
from contextlib import closing


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAIN = PROJECT_ROOT / "deploy" / "update_bundle_src" / "__main__.py"
OUTPUT = PROJECT_ROOT / "deploy" / "solar-dashboard-update.pyz"
STATS_DB_PATH = PROJECT_ROOT / "solar_invertor_web_stats.sqlite3"
PAYLOAD_FILES = (
    "solar_invertor_web.py",
    "favicon.png",
    "generator-mask.png",
    "1258380.png",
    "inverter.svg",
    "home.svg",
    "solar_inverter/__init__.py",
    "solar_inverter/components/__init__.py",
    "solar_inverter/components/api_localization.py",
    "solar_inverter/components/web_dashboard.py",
    "solar_inverter/components/dashboard_template.py",
    "solar_inverter/components/state_consistency.py",
    "solar_inverter/web/index.html",
    "solar_inverter/web/styles/dashboard.css",
    "solar_inverter/web/styles/dashboard-responsive.css",
    "solar_inverter/web/vendor/uPlot.iife.min.js",
    "solar_inverter/web/vendor/uPlot.min.css",
    "solar_inverter/web/vendor/LICENSE-uPlot.txt",
    "solar_inverter/web/data/data-translations.json",
    "solar_inverter/web/scripts/translations.js",
    "solar_inverter/web/scripts/interpretations.js",
    "solar_inverter/web/scripts/renderers.js",
    "solar_inverter/web/scripts/charts.js",
    "solar_inverter/web/scripts/chart-demo-history.js",
    "solar_inverter/web/scripts/chart-rendering.js",
    "solar_inverter/web/scripts/gauges.js",
    "solar_inverter/web/scripts/energy-flow.js",
    "solar_inverter/web/scripts/lcd.js",
    "solar_inverter/web/scripts/app.js",
    "solar_inverter/web/scripts/app-events.js",
    "solar_inverter/services/__init__.py",
    "solar_inverter/services/inverter_service.py",
    "solar_inverter/services/inverter_service_core.py",
    "solar_inverter/services/inverter_service_runtime.py",
    "deploy/solar-inverter-dashboard.service",
)

def ensure_updater_history_schema(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(updater_versions)")}
    additions = {
        "commit_message": "TEXT", "commit_date": "TEXT",
        "source": "TEXT NOT NULL DEFAULT 'local'", "bundle_path": "TEXT",
        "build_output": "TEXT", "created_at": "TEXT",
    }
    for name, declaration in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE updater_versions ADD COLUMN {name} {declaration}")
    connection.execute("UPDATE updater_versions SET created_at = datetime('now') WHERE created_at IS NULL")
    connection.commit()


def record_updater_version(commit_hash: str, commit_message: str, commit_date: str, source: str, bundle_path: str, build_output: str = "") -> bool:
    """Record an updater version in the database."""
    try:
        STATS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(STATS_DB_PATH)) as connection:
            # Ensure table exists
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS updater_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commit_hash TEXT NOT NULL,
                    commit_message TEXT,
                    commit_date TEXT,
                    source TEXT NOT NULL,
                    bundle_path TEXT,
                    build_output TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            ensure_updater_history_schema(connection)
            # Insert record
            connection.execute(
                """
                INSERT INTO updater_versions (commit_hash, commit_message, commit_date, source, bundle_path, build_output)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (commit_hash, commit_message, commit_date, source, bundle_path, build_output)
            )
            connection.commit()
        return True
    except (OSError, sqlite3.Error) as error:
        print(f"Warning: Failed to record updater version: {error}")
        return False


def get_current_commit_info() -> tuple[str, str, str]:
    """Get current git commit hash, message, and date."""
    try:
        # Try to find git
        import shutil
        git_path = shutil.which("git")
        if not git_path:
            # Try common Windows path
            if Path(r"C:\Program Files\Git\bin\git.exe").exists():
                git_path = r"C:\Program Files\Git\bin\git.exe"
            else:
                return "unknown", "Manual build", ""
        
        # Get commit hash
        result = subprocess.run(
            [git_path, "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10
        )
        commit_hash = result.stdout.strip() if result.returncode == 0 else "unknown"
        
        # Get commit message and date
        result = subprocess.run(
            [git_path, "log", "-1", "--pretty=format:%s|%ai"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Split on | to separate message and date
            parts = result.stdout.strip().split("|", 1)
            commit_message = parts[0] if len(parts) > 0 else "Manual build"
            commit_date = parts[1] if len(parts) > 1 else ""
        else:
            commit_message = "Manual build"
            commit_date = ""
        
        return commit_hash, commit_message, commit_date
    except Exception as e:
        print(f"Warning: Failed to get git info: {e}")
        return "unknown", "Manual build", ""


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="solar-dashboard-bundle-") as temporary:
        bundle_root = Path(temporary)
        shutil.copy2(SOURCE_MAIN, bundle_root / "__main__.py")
        for relative_name in PAYLOAD_FILES:
            source = PROJECT_ROOT / relative_name
            if not source.is_file():
                raise FileNotFoundError(source)
            target = bundle_root / "payload" / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        zipapp.create_archive(
            bundle_root,
            OUTPUT,
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    print(f"Created {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
