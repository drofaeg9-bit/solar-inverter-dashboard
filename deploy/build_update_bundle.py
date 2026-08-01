#!/usr/bin/env python3
"""Build the single-file Orange Pi dashboard update archive."""

from __future__ import annotations

import shutil
import tempfile
import zipapp
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAIN = PROJECT_ROOT / "deploy" / "update_bundle_src" / "__main__.py"
OUTPUT = PROJECT_ROOT / "deploy" / "solar-dashboard-update.pyz"
PAYLOAD_FILES = (
    "solar_invertor_web.py",
    "favicon.png",
    "generator-mask.png",
    "1258380.png",
    "inverter.svg",
    "home.svg",
    "solar_inverter/__init__.py",
    "solar_inverter/components/__init__.py",
    "solar_inverter/components/web_dashboard.py",
    "solar_inverter/components/dashboard_template.py",
    "solar_inverter/web/index.html",
    "solar_inverter/web/styles/dashboard.css",
    "solar_inverter/web/styles/dashboard-responsive.css",
    "solar_inverter/web/scripts/translations.js",
    "solar_inverter/web/scripts/interpretations.js",
    "solar_inverter/web/scripts/renderers.js",
    "solar_inverter/web/scripts/charts.js",
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
