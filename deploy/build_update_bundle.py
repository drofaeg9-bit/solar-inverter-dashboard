#!/usr/bin/env python3
"""Build the single-file Orange Pi dashboard update archive."""

from __future__ import annotations

import shutil
import subprocess
import sqlite3
import tempfile
import zipapp
import json
import hashlib
import os
from pathlib import Path
from contextlib import closing


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAIN = PROJECT_ROOT / "deploy" / "update_bundle_src" / "__main__.py"
OUTPUT = PROJECT_ROOT / "deploy" / "solar-dashboard-update.pyz"
STATS_DB_PATH = PROJECT_ROOT / "solar_invertor_web_stats.sqlite3"
UPSTREAM_VERSION_PAYLOAD = ".solar-dashboard-upstream.json"
PAYLOAD_MANIFEST = ".solar-dashboard-payload.json"
EXCLUDED_PAYLOAD_DIRECTORIES = frozenset({
    ".git", ".venv", "node_modules", "__pycache__", "register_logs", ".pytest_cache",
    ".gradle", "build",
})
EXCLUDED_PAYLOAD_FILES = frozenset({
    "deploy/solar-dashboard-update.pyz",
    "solar_invertor_web_stats.sqlite3",
    "config/home-assistant_v2.db",
})


def project_payload_files() -> tuple[str, ...]:
    """Return every deployable source file in this project workspace."""
    files: list[str] = []
    for directory, child_directories, filenames in os.walk(PROJECT_ROOT):
        child_directories[:] = [
            name for name in child_directories
            if name not in EXCLUDED_PAYLOAD_DIRECTORIES
        ]
        directory_path = Path(directory)
        for filename in filenames:
            source = directory_path / filename
            relative_name = source.relative_to(PROJECT_ROOT).as_posix()
            if relative_name in EXCLUDED_PAYLOAD_FILES or source.suffix in {".pyc", ".pyo"}:
                continue
            files.append(relative_name)
    return tuple(sorted(files))

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


def get_github_repository() -> str:
    """Return the origin GitHub owner/repository for the archive metadata."""
    try:
        remote = subprocess.run(
            [shutil.which("git") or "git", "remote", "get-url", "origin"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip().removesuffix(".git")
        if remote.startswith("https://github.com/"):
            return remote.removeprefix("https://github.com/")
        if remote.startswith("git@github.com:"):
            return remote.removeprefix("git@github.com:")
    except (OSError, subprocess.SubprocessError):
        pass
    return "santaes/solar-inverter-dashboard"


def main() -> None:
    print("Collecting deployable project files...", flush=True)
    project_files = project_payload_files()
    print(f"Packing {len(project_files)} project files...", flush=True)
    with tempfile.TemporaryDirectory(prefix="solar-dashboard-bundle-") as temporary:
        bundle_root = Path(temporary)
        shutil.copy2(SOURCE_MAIN, bundle_root / "__main__.py")
        payload_files = (*project_files, UPSTREAM_VERSION_PAYLOAD)
        for relative_name in payload_files:
            if relative_name == UPSTREAM_VERSION_PAYLOAD:
                continue
            source = PROJECT_ROOT / relative_name
            if not source.is_file():
                raise FileNotFoundError(source)
            target = bundle_root / "payload" / relative_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        commit, message, committed_at = get_current_commit_info()
        metadata_path = bundle_root / "payload" / UPSTREAM_VERSION_PAYLOAD
        metadata_path.write_text(
            json.dumps(
                {
                    "repository": get_github_repository(), "branch": "main", "commit": commit,
                    "message": message, "committed_at": committed_at,
                },
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
        manifest = {
            "files": {
                relative_name: hashlib.sha256(
                    (bundle_root / "payload" / relative_name).read_bytes()
                ).hexdigest()
                for relative_name in payload_files
            }
        }
        (bundle_root / "payload" / PAYLOAD_MANIFEST).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        zipapp.create_archive(
            bundle_root,
            OUTPUT,
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    print(f"Created {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
