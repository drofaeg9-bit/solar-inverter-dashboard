#!/usr/bin/env python3
"""Install or update the Solar Inverter Dashboard from one zipapp file."""

from __future__ import annotations

import argparse
import compileall
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


APPLICATION_ROOT = Path("/opt/solar_assistant")
SERVICE_NAME = "solar-inverter-dashboard.service"
SERVICE_TARGET = Path("/etc/systemd/system") / SERVICE_NAME
SERVICE_USER = "solar-dashboard"
SERVICE_GROUP = "solar-dashboard"
HEALTH_URL = "http://127.0.0.1:8080/api/state"
UPDATER_VERSION = "4"

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
)
SERVICE_PAYLOAD = "deploy/solar-inverter-dashboard.service"


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command and echo it for an auditable update log."""
    print("+", " ".join(command), flush=True)
    return subprocess.run(command, check=check, text=True)


def archive_path() -> Path:
    """Return the running zipapp path."""
    return Path(sys.argv[0]).resolve()


def extract_payload(destination: Path) -> None:
    """Extract only the declared application payload."""
    with zipfile.ZipFile(archive_path()) as archive:
        names = set(archive.namelist())
        expected = {f"payload/{name}" for name in (*PAYLOAD_FILES, SERVICE_PAYLOAD)}
        missing = sorted(expected - names)
        if missing:
            raise RuntimeError(f"Update archive is incomplete: {', '.join(missing)}")
        for name in (*PAYLOAD_FILES, SERVICE_PAYLOAD):
            source = f"payload/{name}"
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(source))


def validate_payload(payload_root: Path) -> None:
    """Compile the complete Python payload before touching the installation."""
    print("Validating bundled Python files...", flush=True)
    valid = compileall.compile_dir(
        str(payload_root / "solar_inverter"),
        quiet=1,
        force=True,
    )
    valid = compileall.compile_file(
        str(payload_root / "solar_invertor_web.py"),
        quiet=1,
        force=True,
    ) and valid
    if not valid:
        raise RuntimeError("The bundled Python source did not compile")


def require_root() -> None:
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        raise PermissionError("Run the update with: sudo python3 solar-dashboard-update.pyz")


def ensure_runtime() -> None:
    """Install external runtime packages when they are absent."""
    if shutil.which("systemctl") is None:
        raise RuntimeError("systemd is required but systemctl was not found")
    packages: list[str] = []
    if shutil.which("mbpoll") is None:
        packages.append("mbpoll")
    if not Path("/usr/share/zoneinfo/Europe/Madrid").is_file():
        packages.append("tzdata")
    if packages:
        if shutil.which("apt-get") is None:
            raise RuntimeError(
                f"Missing packages ({', '.join(packages)}) and apt-get is unavailable"
            )
        run(["apt-get", "update"])
        run(["apt-get", "install", "-y", *packages])


def ensure_service_account() -> tuple[int, int]:
    """Create the restricted dashboard account when necessary."""
    import pwd

    try:
        account = pwd.getpwnam(SERVICE_USER)
    except KeyError:
        run([
            "useradd",
            "--system",
            "--user-group",
            "--home-dir",
            str(APPLICATION_ROOT),
            "--shell",
            "/usr/sbin/nologin",
            SERVICE_USER,
        ])
        account = pwd.getpwnam(SERVICE_USER)
    run(["usermod", "-aG", "dialout", SERVICE_USER])
    return account.pw_uid, account.pw_gid


def atomic_install(source: Path, target: Path, mode: int, uid: int, gid: int) -> None:
    """Replace one file atomically without removing unrelated runtime data."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.update-{os.getpid()}")
    try:
        shutil.copyfile(source, temporary)
        os.chmod(temporary, mode)
        os.chown(temporary, uid, gid)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def install_payload(payload_root: Path, uid: int, gid: int) -> None:
    """Install application files while preserving SQLite data and register logs."""
    APPLICATION_ROOT.mkdir(parents=True, exist_ok=True)
    os.chown(APPLICATION_ROOT, uid, gid)
    for relative_name in PAYLOAD_FILES:
        atomic_install(
            payload_root / relative_name,
            APPLICATION_ROOT / relative_name,
            0o644,
            uid,
            gid,
        )
    atomic_install(payload_root / SERVICE_PAYLOAD, SERVICE_TARGET, 0o644, 0, 0)


def record_installed_version(uid: int, gid: int) -> None:
    """Record this local updater installation without requiring Git metadata."""
    database_path = APPLICATION_ROOT / "solar_invertor_web_stats.sqlite3"
    checksum = hashlib.sha256(archive_path().read_bytes()).hexdigest().upper()
    with sqlite3.connect(database_path) as connection:
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
        connection.execute(
            """
            INSERT INTO updater_versions
                (commit_hash, commit_message, commit_date, source, bundle_path, build_output)
            VALUES (?, ?, datetime('now'), 'installer', ?, ?)
            """,
            (f"updater-{UPDATER_VERSION}", f"Updater {UPDATER_VERSION}", archive_path().name, f"SHA-256 {checksum}"),
        )
        connection.commit()
    os.chown(database_path, uid, gid)
    print(f"Recorded Updater {UPDATER_VERSION} installation.", flush=True)


def wait_for_health() -> None:
    """Wait briefly for the restarted local API."""
    last_error = "no response"
    for _ in range(15):
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    print(f"Dashboard API is healthy: {HEALTH_URL}", flush=True)
                    return
                last_error = f"HTTP {response.status}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last_error = str(error)
        time.sleep(1)
    run(["systemctl", "--no-pager", "--full", "status", SERVICE_NAME], check=False)
    run(["journalctl", "-u", SERVICE_NAME, "-n", "50", "--no-pager"], check=False)
    raise RuntimeError(f"Dashboard health check failed: {last_error}")


def install() -> None:
    require_root()
    ensure_runtime()
    uid, gid = ensure_service_account()
    with tempfile.TemporaryDirectory(prefix="solar-dashboard-update-") as temporary:
        payload_root = Path(temporary)
        extract_payload(payload_root)
        validate_payload(payload_root)
        run(["systemctl", "stop", SERVICE_NAME], check=False)
        install_payload(payload_root, uid, gid)
        record_installed_version(uid, gid)
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", SERVICE_NAME])
    run(["systemctl", "restart", SERVICE_NAME])
    wait_for_health()
    if shutil.which("tailscale"):
        run(["tailscale", "serve", "status"], check=False)
    print("Solar Inverter Dashboard update completed successfully.", flush=True)


def check_bundle() -> None:
    with tempfile.TemporaryDirectory(prefix="solar-dashboard-check-") as temporary:
        payload_root = Path(temporary)
        extract_payload(payload_root)
        validate_payload(payload_root)
    print(f"Bundle is valid and contains {len(PAYLOAD_FILES)} application files.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the archive without installing or changing the system",
    )
    arguments = parser.parse_args()
    try:
        if arguments.check:
            check_bundle()
        else:
            install()
        return 0
    except (OSError, RuntimeError, PermissionError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
