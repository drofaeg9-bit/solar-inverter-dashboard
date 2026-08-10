from __future__ import annotations

import ast
import json
import re
import runpy
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "solar_inverter" / "web"
SCRIPT_NAMES = (
    "translations.js",
    "interpretations.js",
    "renderers.js",
    "charts.js",
    "chart-demo-history.js",
    "chart-rendering.js",
    "gauges.js",
    "energy-flow.js",
    "lcd.js",
    "app.js",
    "app-events.js",
)


def dashboard_css() -> str:
    return "\n".join(
        (WEB_ROOT / "styles" / name).read_text(encoding="utf-8")
        for name in ("dashboard.css", "dashboard-responsive.css")
    )


def script_source(*names: str) -> str:
    return "\n".join(
        (WEB_ROOT / "scripts" / name).read_text(encoding="utf-8")
        for name in names
    )


def inverter_service_source() -> str:
    services = ROOT / "solar_inverter" / "services"
    return "\n".join(
        (services / name).read_text(encoding="utf-8")
        for name in ("inverter_service_core.py", "inverter_service_runtime.py")
    )


class DashboardAssetTests(unittest.TestCase):
    def test_api_localization_repairs_legacy_utf8_and_chart_history_is_packaged(self) -> None:
        from solar_inverter.components.api_localization import repair_legacy_text

        self.assertEqual(
            repair_legacy_text("\u00d0\u00a0\u00d0\u00b5\u00d0\u00b3\u00d1\u0096\u00d1\u0081\u00d1\u0082\u00d1\u0080"),
            "\u0420\u0435\u0433\u0456\u0441\u0442\u0440",
        )
        self.assertEqual(repair_legacy_text("\u00e2\u20ac\u201d"), "\u2014")
        for manifest in (ROOT / "deploy" / "build_update_bundle.py", ROOT / "deploy" / "update_bundle_src" / "__main__.py"):
            self.assertIn("solar_inverter/services/chart_history.py", manifest.read_text(encoding="utf-8"))

    def test_light_theme_is_dimmed_and_keeps_readable_contrast(self) -> None:
        css = dashboard_css()
        self.assertIn("--bg: #eef2f4", css)
        self.assertIn("--panel: rgba(248, 250, 251, .96)", css)
        self.assertIn(':root[data-theme="light"] .energy-inverter', css)
        self.assertIn(':root[data-theme="light"] .progress', css)

        def luminance(colour: str) -> float:
            channels = [int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in channels]
            return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2]

        def contrast(first: str, second: str) -> float:
            high, low = sorted((luminance(first), luminance(second)), reverse=True)
            return (high + .05) / (low + .05)

        self.assertGreaterEqual(contrast("#243742", "#eef2f4"), 7)
        self.assertGreaterEqual(contrast("#61737d", "#f8fafb"), 4.5)
        for category_colour in (
            "#8b5e20", "#2e7482", "#70608f",
            "#397665", "#3e708d", "#985a2e",
        ):
            self.assertGreaterEqual(contrast(category_colour, "#eef2f4"), 4.5)
        self.assertGreaterEqual(contrast("#77868e", "#f2f5f7"), 3)
        self.assertGreaterEqual(contrast("#77868e", "#ffffff"), 3)
        self.assertGreaterEqual(contrast("#245f7a", "#eef2f4"), 3)
        self.assertGreaterEqual(contrast("#71849b", "#0a1625"), 3)
        self.assertGreaterEqual(contrast("#71849b", "#15263b"), 3)
        self.assertGreaterEqual(contrast("#7dd3fc", "#07111f"), 3)
        for category_colour in (
            "#fbbf24", "#22d3ee", "#a78bfa", "#34d399",
            "#60a5fa", "#fb923c", "#fb7185",
        ):
            self.assertGreaterEqual(contrast(category_colour, "#15263b"), 3)

    def test_interaction_work_is_deferred_until_after_next_paint(self) -> None:
        css = dashboard_css()
        charts = script_source("charts.js", "chart-demo-history.js", "chart-rendering.js")
        app = script_source("app.js", "app-events.js")
        self.assertNotIn("backdrop-filter: blur(18px)", css)
        self.assertIn("scrollbar-gutter: stable", css)
        self.assertIn("position: fixed; z-index: 1000", css)
        self.assertIn("gaugeSelectionRenderPending", charts)
        self.assertIn("requestAnimationFrame(() => window.setTimeout", charts)
        self.assertIn("requestAnimationFrame(() => window.setTimeout(drawAllCharts, 0))", app)
        self.assertIn("window.requestIdleCallback(renderPendingRegisters, {timeout: 750})", app)
        self.assertIn("const REGISTER_RENDER_LIMIT = 80", app)
        self.assertIn("const visible = shown.slice(0, registerRenderLimit)", app)
        self.assertIn("content-visibility: auto", css)
        self.assertNotIn("canvas.clientWidth", charts)
        self.assertNotIn("canvas.clientHeight", charts)
        self.assertNotIn("canvas.getBoundingClientRect()", charts)
        self.assertIn("new ResizeObserver", charts)
        self.assertIn("new IntersectionObserver", charts)
        self.assertIn("[...visibleChartCanvases].forEach(host =>", charts)
        self.assertIn("new uPlot(chartOptions", charts)
        self.assertIn("const chartInteractionStates = new WeakMap()", charts)
        self.assertIn("state.userZoomed = true", charts)
        self.assertIn("plot.setData(data, !state?.userZoomed)", charts)
        self.assertIn("const CHART_UPDATE_ANIMATION_MS = 260", charts)
        self.assertIn("const eased = progress * progress * (3 - 2 * progress)", charts)
        self.assertIn("requestAnimationFrame(animate)", charts)
        self.assertIn("prefers-reduced-motion: reduce", charts)
        self.assertIn("destroyDetachedCharts()", charts)
        self.assertIn("outline: 3px solid var(--focus-ring)", css)
        self.assertIn("--ui-border: #71849b", css)
        self.assertIn("--ui-border: #77868e", css)
        self.assertIn("scheduleRegisterRender(demoRegisterRows)", charts)
        self.assertIn("function demoFallbackValue(register, elapsedSeconds)", charts)
        self.assertIn("item.available = true", charts)
        self.assertIn("scheduleRegisterRender(displayedRegisters)", app)
        self.assertIn("TTN-INV external Modbus map V1.31", charts)
        self.assertIn("[16641, 2], [16642, 0]", charts)
        self.assertIn("[16646, 60], [16647, 10], [16648, 0]", charts)
        self.assertIn("[16653, 46], [16654, 52], [16655, 154], [16656, 264]", charts)
        self.assertNotIn("register.register === 157", charts)
        service_source = (
            ROOT / "solar_inverter" / "services" / "inverter_service_core.py"
        ).read_text(encoding="utf-8")
        chart_history = (
            ROOT / "solar_inverter" / "services" / "chart_history.py"
        ).read_text(encoding="utf-8")
        self.assertIn("CHART_HISTORY_RAW_RETENTION_SECONDS = 48 * 60 * 60", chart_history)
        self.assertIn("CHART_HISTORY_AGGREGATE_RETENTION_SECONDS = 90 * 24 * 60 * 60", chart_history)
        self.assertIn("CREATE TABLE IF NOT EXISTS chart_history_daily", chart_history)
        service_module = ast.parse(service_source)
        known_registers: set[int] = set()
        for node in service_module.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "KNOWN_REGISTERS"
                for target in node.targets
            ):
                known_registers = set(ast.literal_eval(node.value))
                break
        values_start = charts.index("values: new Map([")
        values_end = charts.index("])\n      };", values_start)
        demo_registers = {
            int(register)
            for register in re.findall(r"\[(\d+),", charts[values_start:values_end])
        }
        self.assertEqual(known_registers - demo_registers, set())
        self.assertIn("content-visibility: auto; contain-intrinsic-size: auto 300px", css)
        self.assertIn("const requestIntervals = [500, 1000, 2000, 5000, 10000]", app)
        self.assertIn("const hiddenRefreshInterval = 30000", app)
        self.assertIn("readSeconds: data.read_seconds.toFixed(2)", app)
        self.assertIn("const configuredSeconds = (requestIntervals[data.poll_rate_index] ?? 2000) / 1000", app)
        self.assertIn("renderCycleStatus(lastData)", app)
        self.assertIn("const CHARTS_PER_PAGE = 12", charts)
        self.assertIn("selected.slice(pageStart, pageStart + CHARTS_PER_PAGE)", charts)
        self.assertIn("function scheduleChartsViewRender()", charts)
        self.assertIn("scheduleChartsViewRender();", app)
        self.assertIn("data-chart-page", charts)
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('role="tabpanel" aria-labelledby="dashboard-tab"', html)
        self.assertIn('aria-controls="charts-view"', html)
        self.assertIn('data-i18n="lcdUpKey"', html)
        self.assertIn('id="register-load-more"', html)
        self.assertIn("button.tabIndex = active ? 0 : -1", app)
        self.assertIn("['ArrowLeft', 'ArrowRight', 'Home', 'End']", app)
        gauges = (WEB_ROOT / "scripts" / "gauges.js").read_text(encoding="utf-8")
        self.assertIn("const DASHBOARD_GAUGES_PER_PAGE = 12", gauges)
        self.assertIn("gauges.slice(pageStart, pageStart + DASHBOARD_GAUGES_PER_PAGE)", gauges)
        self.assertIn("data-dashboard-page", gauges)
        self.assertIn('id="dashboard-pagination-host"', html)
        self.assertIn("paginationHost.innerHTML = dashboardGaugePaginationMarkup(pageCount)", gauges)
        self.assertIn("+ dashboardGaugePaginationMarkup(pageCount)", gauges)
        self.assertIn("renderGauges(gauges.slice(pageStart, pageStart + DASHBOARD_GAUGES_PER_PAGE), pageCount)", gauges)
        self.assertIn("dashboardGaugeToolbar.addEventListener('click', handleDashboardPaginationClick)", app)
        self.assertIn("var(--flow-solar-colour)", gauges)
        self.assertIn("var(--flow-grid-colour)", gauges)
        self.assertIn("const colour = chartColour(item, index)", charts)
        self.assertIn("styles.getPropertyValue(property).trim()", charts)
        self.assertIn("--flow-generator-colour: #fb923c", css)
        self.assertIn("--flow-generator-colour: #985a2e", css)

    def test_flow_connectors_stay_behind_every_card(self) -> None:
        css = dashboard_css()
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("display: grid; isolation: isolate", css)
        self.assertIn("position: relative; z-index: 1; align-self: stretch", css)
        self.assertIn("position: absolute; inset: -8px; display: block", css)
        self.assertIn("width: calc(100% + 16px); height: calc(100% + 16px)", css)
        self.assertIn(".flow-connector.active { z-index: 1", css)
        self.assertIn("position: relative; z-index: 2; display: flex", css)
        self.assertNotIn(".flow-connector.active { z-index: 4", css)
        self.assertIn(
            'class="flow-line flow-line-mobile" x1="0" y1="100" x2="100" y2="0"',
            html,
        )
        self.assertIn(
            'class="flow-line flow-line-mobile" x1="0" y1="0" x2="100" y2="100"',
            html,
        )
        self.assertIn(".flow-generator .flow-line-mobile { stroke-linecap: round }", css)

    def test_gauges_and_graphs_use_energy_flow_component_colours(self) -> None:
        gauges_path = WEB_ROOT / "scripts" / "gauges.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            const source = fs.readFileSync(process.argv[1], 'utf8');
            eval(source + `
              const expected = new Map([
                [81, 'var(--flow-grid-colour)'],
                [85, 'var(--flow-generator-colour)'],
                [92, 'var(--flow-home-colour)'],
                [94, 'var(--flow-inverter-colour)'],
                [129, 'var(--flow-battery-colour)'],
                [151, 'var(--flow-solar-colour)'],
                [164, 'var(--flow-battery-colour)'],
                [172, 'var(--flow-inverter-colour)'],
                [176, 'var(--flow-home-colour)'],
                [184, 'var(--flow-grid-colour)'],
                [448, 'var(--flow-grid-colour)'],
                [541, 'var(--flow-home-colour)'],
                [818, 'var(--flow-inverter-colour)'],
                [823, 'var(--flow-solar-colour)'],
                [16651, 'var(--flow-battery-colour)'],
                [16655, 'var(--flow-grid-colour)']
              ]);
              const matches = [...expected].every(([register, colour]) => {
                const item = {register, key: 'register-' + register};
                return registerEnergyFlowColour(register) === colour
                  && dashboardGaugeColour(item) === colour
                  && chartColour(item) === colour;
              });
              console.log(JSON.stringify({
                matches,
                customSolar: diagramGaugeColour({register: 20000, label: 'Solar custom input'}),
                customUnknown: diagramGaugeColour({register: 20001, label: 'Custom counter'})
              }));
            `);
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(gauges_path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(
            json.loads(result.stdout),
            {
                "matches": True,
                "customSolar": "var(--flow-solar-colour)",
                "customUnknown": None,
            },
        )

    def test_disabled_buttons_use_localized_unavailable_hints(self) -> None:
        css = dashboard_css()
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = script_source("app.js", "app-events.js")
        self.assertIn("button:disabled { cursor: not-allowed", css)
        self.assertIn('content: "⊘"', css)
        self.assertIn('data-disabled-reason="startLoggingFirst"', html)
        self.assertIn("function refreshDisabledButtonHints", app)
        self.assertIn("attributeFilter: ['disabled']", app)

    def test_template_loads_extracted_assets_in_dependency_order(self) -> None:
        from solar_inverter.components.dashboard_template import WEB_DASHBOARD

        self.assertEqual(WEB_DASHBOARD.count("/*__INITIAL_STATE__*/null"), 1)
        self.assertNotIn("/*__DASHBOARD_CSS__*/", WEB_DASHBOARD)
        self.assertNotIn("__ASSET_VERSION__", WEB_DASHBOARD)
        self.assertRegex(WEB_DASHBOARD, r"energy-flow\.js\?v=[0-9a-f]{12}")
        self.assertIn("<style>", WEB_DASHBOARD)
        self.assertIn(".energy-flow-diagram", WEB_DASHBOARD)
        positions = [
            WEB_DASHBOARD.index(f'/static/scripts/{name}') for name in SCRIPT_NAMES
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(WEB_DASHBOARD.count("<script defer src="), len(SCRIPT_NAMES) + 1)
        self.assertIn("/static/vendor/uPlot.iife.min.js", WEB_DASHBOARD)
        self.assertNotIn("const UI_TRANSLATIONS", WEB_DASHBOARD)
        self.assertNotIn("function renderEnergyFlow", WEB_DASHBOARD)

    def test_static_assets_use_compression_and_long_lived_caching(self) -> None:
        server = (ROOT / "solar_inverter" / "components" / "web_dashboard.py").read_text(encoding="utf-8")
        css = dashboard_css()
        self.assertIn('gzip.compress(body, compresslevel=5, mtime=0)', server)
        self.assertIn('cache_control="public, max-age=31536000, immutable"', server)
        self.assertIn('cache_control="no-store, no-cache, must-revalidate"', server)
        self.assertIn("/assets/generator-mask.png?v=__ASSET_VERSION__", css)
        self.assertLess((ROOT / "generator-mask.png").stat().st_size, 20_000)

    def test_timeline_charts_use_local_uplot_and_interactive_modal(self) -> None:
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        charts = script_source("charts.js", "chart-rendering.js", "chart-demo-history.js", "app.js")
        css = dashboard_css()
        self.assertIn('/static/vendor/uPlot.iife.min.js', html)
        self.assertNotIn('rel="stylesheet" href="/static/vendor/uPlot.min.css', html)
        self.assertIn("function ensureChartStylesheet()", charts)
        self.assertIn("document.head.append(link)", charts)
        self.assertIn("ensureChartStylesheet().then", charts)
        self.assertIn('id="chart-modal"', html)
        self.assertIn('width: 80vw', css)
        self.assertIn('height: 80vh', css)
        self.assertIn("function isTimelineValue(item)", charts)
        self.assertIn("const ENERGY_CONSUMPTION_REGISTERS = new Set", charts)
        self.assertIn("176, 177, 178, 179", charts)
        self.assertIn("184, 185, 186, 187", charts)
        self.assertIn("ENERGY_CONSUMPTION_REGISTERS.has(register)", charts)
        self.assertIn("[179, 'lifetime']", charts)
        self.assertIn("[187, 'lifetime']", charts)
        self.assertIn("function chartPeriodForItem(item", charts)
        self.assertNotIn("chart-period-select", html)
        self.assertNotIn("refreshChartsWithPeriod", charts)
        self.assertIn("async function hydrateChartHistory()", charts)
        self.assertIn("/api/historical?period=${encodeURIComponent(period)}", charts)
        self.assertIn("selectedChartPeriodLabel", charts)
        self.assertIn("trimChartHistory(history, now, item)", charts)
        self.assertIn("chartPeriodValue", charts)
        self.assertNotIn("selectedSummary: 'Выбрано значений: {count} · последние 2 минуты'", charts)
        self.assertIn("/^(?:k?wh)$/i.test(unit)", charts)
        self.assertNotIn("if (value === null && !timelineCapable) return", charts)
        self.assertIn("function synchronizeTimelineCharts()", charts)
        self.assertIn("const timelineKeys = new Set(timelineDefinitions().map(item => item.key))", charts)
        self.assertIn("const selected = timelineDefinitions().map(item => item.key)", charts)
        self.assertIn("const chartValue = value === null", charts)
        self.assertIn("cursor: {drag: {x: false, y: false, setScale: false}", charts)
        self.assertIn("addEventListener('wheel'", charts)
        self.assertIn("addEventListener('pointerdown', pointerDown)", charts)
        self.assertIn("addEventListener('pointermove', pointerMove", charts)
        self.assertIn("const shift = -deltaPixels * (pan.maximum - pan.minimum) / width", charts)
        self.assertIn("const pointers = new Map()", charts)
        self.assertIn("initialRange * pinch.distance / distance", charts)
        self.assertIn("event.pointerType === 'touch' && !isModal", charts)
        self.assertIn("resetChartZoom(plot)", charts)
        self.assertIn(".chart-modal-host .u-over { touch-action: none }", css)
        self.assertIn("height: min(84dvh, calc(100dvh - 12px))", css)
        self.assertIn("function constrainedTimeScale", charts)
        self.assertIn("ticks.map(timestamp => chartAxisTime(plot, timestamp))", charts)
        self.assertIn("space: host.clientWidth < 480 ? 90 : 70", charts)
        self.assertIn("month: '2-digit', hour: '2-digit', minute: '2-digit'", charts)
        self.assertIn("if (unique.at(-1)?.time === point.time)", charts)
        self.assertIn("function continuousDemoChartValue(item, history)", charts)
        self.assertIn("previous + scale * .01", charts)
        self.assertIn("chart-point-tooltip", charts)

    def test_all_energy_charts_are_automatic_and_dashboard_gauges_remain_optional(self) -> None:
        charts = (WEB_ROOT / "scripts" / "charts.js").read_text(encoding="utf-8")
        events = (WEB_ROOT / "scripts" / "app-events.js").read_text(encoding="utf-8")
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn("function synchronizeTimelineCharts()", charts)
        self.assertIn("const selected = timelineDefinitions().map(item => item.key)", charts)
        self.assertNotIn("renderChartValueList", charts)
        self.assertNotIn("#chart-value-list", events)
        self.assertNotIn("chart-selector", html)
        self.assertNotIn("chart-select-all", html)

    def test_energy_flow_uses_physical_live_grid_and_generator_registers(self) -> None:
        flow = (WEB_ROOT / "scripts" / "energy-flow.js").read_text(encoding="utf-8")
        self.assertIn("firstRegister([81, 433])", flow)
        self.assertIn("firstRegister([85])", flow)
        self.assertIn("firstRegister([86])", flow)
        self.assertIn("firstRegister([88])", flow)
        self.assertIn("firstRegister([69])", flow)
        self.assertIn("firstRegister([67, 325])", flow)
        self.assertNotIn("firstRegister([68])", flow)
        self.assertNotIn("firstRegister([70, 322])", flow)
        self.assertIn("firstRegister([84, 436])", flow)
        self.assertIn("firstRegister([161, 153, 156])", flow)
        self.assertIn("const liveMeasurementsFresh = chartDemoRunning || Boolean(data.online)", flow)
        self.assertIn("grid: raw & 0x03", flow)
        self.assertIn("generator: (raw >> 2) & 0x03", flow)
        self.assertIn("pv1: (raw >> 4) & 0x03", flow)
        self.assertIn("output: (raw >> 6) & 0x03", flow)
        self.assertIn("battery: (raw >> 8) & 0x07", flow)
        self.assertIn("charging: (raw >> 11) & 0x07", flow)
        self.assertIn("pv2: (raw >> 14) & 0x03", flow)
        self.assertIn("rectifierToGrid: Boolean(raw & 1 << 7)", flow)
        self.assertIn("batteryToInverter: Boolean(raw & 1 << 8)", flow)
        self.assertIn("inverterToMainOutput: Boolean(raw & 1 << 9)", flow)
        self.assertIn("const flowSuppressedByState = [0, 1, 7, 8, 10].includes(inverterState)", flow)
        self.assertIn("`${routeSources.join(' + ')} → ${routeDestinations.join(' + ')}`", flow)
        self.assertIn("parallelTopologyCode(parallelState)", flow)
        self.assertIn("classList.toggle('disconnected', !generatorConnected)", flow)
        self.assertIn("classList.toggle('disconnected', !gridAvailable)", flow)

    def test_poll_timing_reports_real_cycles_and_accounts_for_postprocessing(self) -> None:
        service = inverter_service_source()
        server = (ROOT / "solar_inverter" / "components" / "web_dashboard.py").read_text(encoding="utf-8")
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('"read_seconds": 0.0', service)
        self.assertIn("POLL_RATES = [0.5, 1.0, 2.0, 5.0, 10.0]", service)
        self.assertIn('"poll_rate_index": 2', service)
        self.assertIn('<option value="2" data-i18n="interval2">', html)
        self.assertIn('<option value="3" data-i18n="interval5">', html)
        self.assertIn('<option value="4" data-i18n="interval10">', html)
        self.assertIn("cycle_duration = round(cycle_interval or read_duration, 2)", service)
        self.assertIn("cycle_work_duration = time.monotonic() - started", service)
        self.assertIn("poll_rate - cycle_work_duration", service)
        self.assertIn('"read_seconds": snapshot["read_seconds"]', server)

    def test_static_route_map_contains_every_referenced_asset(self) -> None:
        from solar_inverter.components.web_dashboard import DASHBOARD_STATIC_PATHS

        expected = {
            f"/static/{path.relative_to(WEB_ROOT).as_posix()}"
            for path in WEB_ROOT.rglob("*")
            if path.is_file() and path.name != "index.html"
        }
        self.assertEqual(set(DASHBOARD_STATIC_PATHS), expected)
        self.assertTrue(all(path.is_file() for path in DASHBOARD_STATIC_PATHS.values()))

    def test_translation_catalog_has_all_supported_languages(self) -> None:
        source = (WEB_ROOT / "scripts" / "translations.js").read_text(encoding="utf-8")
        self.assertIn("const UI_TRANSLATIONS", source)
        self.assertIn("const DATA_TRANSLATIONS", source)
        for language in ("uk", "ru", "en"):
            self.assertIn(f"      {language}: {{", source)
        self.assertIn("function localizeDataText", source)
        self.assertIn("function localizeApiField", source)
        for obsolete in (
            "Код конфігурації 66",
            "Код конфігурації 67",
            "Системне значення 68",
            "Упаковане знакове значення 69",
        ):
            self.assertNotIn(obsolete, source)

    def test_api_state_localizes_metadata_and_preserves_source_text(self) -> None:
        import threading
        import urllib.request
        from http.server import ThreadingHTTPServer

        from solar_inverter.components.web_dashboard import (
            DashboardHandler,
            localize_api_text,
            resolve_api_language,
            web_state,
        )

        self.assertEqual(resolve_api_language("ru", "en-US,en;q=.9"), "ru")
        self.assertEqual(resolve_api_language("", "fr, en;q=.8, ru;q=.9"), "ru")
        self.assertEqual(resolve_api_language("de", "fr"), "uk")
        self.assertEqual(localize_api_text("Немає даних mbpoll", "ru"), "Нет данных mbpoll")
        self.assertEqual(localize_api_text("Немає даних mbpoll", "en"), "No mbpoll data")

        snapshot = web_state("ru")
        self.assertEqual(snapshot["language"], "ru")
        self.assertRegex(snapshot["dashboard_version"], r"^[0-9a-f]{12}$")
        self.assertEqual(snapshot["dashboard_instance"], web_state("en")["dashboard_instance"])
        grid_voltage = next(item for item in snapshot["registers"] if item["register"] == 81)
        self.assertEqual(grid_voltage["name"], "Напряжение сети, фаза A")
        self.assertEqual(grid_voltage["name_source"], "Напруга мережі, фаза A")
        self.assertEqual(grid_voltage["group"], "AC")
        self.assertIsNone(grid_voltage["value"])
        self.assertIn("сырое значение × 0.1 V", grid_voltage["description"])
        bms_state = next(item for item in snapshot["registers"] if item["register"] == 66)
        self.assertIn("0 — поиск", bms_state["description"])
        self.assertIn("1 — CAN", bms_state["description"])
        serial_word = next(item for item in snapshot["registers"] if item["register"] == 1)
        self.assertIn("ASCII-символы 1–2", serial_word["description"])
        self.assertEqual(serial_word["display"], "—")
        protocol_major = next(item for item in snapshot["registers"] if item["register"] == 17)
        self.assertEqual(protocol_major["display"], "—")
        self.assertIn("R18", protocol_major["description"])
        fault_mask = next(item for item in snapshot["registers"] if item["register"] == 71)
        self.assertIn("b0", fault_mask["description"])
        self.assertIn("b15", fault_mask["description"])
        self.assertTrue(all(item["description"] for item in snapshot["registers"]))
        self.assertIn("error_source", snapshot)
        self.assertIn("error_source", snapshot["register_log"])

        app = (WEB_ROOT / "scripts" / "app.js").read_text(encoding="utf-8")
        self.assertEqual(app.count("/api/state?lang=${encodeURIComponent(currentLanguage)}"), 2)
        self.assertIn("data.dashboard_instance !== dashboardInstance", app)
        self.assertIn("function reloadDashboardForVersion(data)", app)
        self.assertIn("fetch(`/api/version?_=${Date.now()}`", app)
        self.assertIn("nextUrl.searchParams.set('_dashboard', data.dashboard_instance || data.dashboard_version)", app)
        self.assertIn("window.location.replace(nextUrl.toString())", app)
        self.assertIn("let dashboardVersion = window.__INITIAL_STATE__?.dashboard_version || ''", app)
        self.assertIn("const versionChanged = Boolean(", app)
        self.assertIn("!instanceChanged && !versionChanged", app)
        self.assertIn("!lastData?.paused", app)
        self.assertIn("document.hidden ? 30000 : 5000", app)
        self.assertIn("pageIsActive = false", app)
        self.assertIn("item.description || ''", app)
        self.assertIn('class="register-meaning"', app)
        self.assertIn('data-i18n="meaning"', (WEB_ROOT / "index.html").read_text(encoding="utf-8"))

        server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/state?lang=en"
            with urllib.request.urlopen(url, timeout=5) as response:
                served = json.load(response)
                self.assertEqual(response.headers["Content-Language"], "en")
                self.assertEqual(served["language"], "en")
                served_r81 = next(
                    item for item in served["registers"] if item["register"] == 81
                )
                self.assertEqual(served_r81["name"], "Grid voltage, phase A")
            version_url = f"http://127.0.0.1:{server.server_port}/api/version"
            with urllib.request.urlopen(version_url, timeout=5) as response:
                version = json.load(response)
                self.assertEqual(version["dashboard_instance"], snapshot["dashboard_instance"])
                self.assertEqual(response.headers["Cache-Control"], "no-store")
            history_url = f"http://127.0.0.1:{server.server_port}/api/updater-history"
            with urllib.request.urlopen(history_url, timeout=5) as response:
                history = json.load(response)
                self.assertIsInstance(history["history"], list)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_updater_four_records_local_installations_without_github_ui(self) -> None:
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        events = (WEB_ROOT / "scripts" / "app-events.js").read_text(encoding="utf-8")
        installer = (ROOT / "deploy" / "update_bundle_src" / "__main__.py").read_text(encoding="utf-8")
        runtime = (ROOT / "solar_inverter" / "services" / "inverter_service_runtime.py").read_text(encoding="utf-8")
        server_source = (ROOT / "solar_inverter" / "components" / "web_dashboard.py").read_text(encoding="utf-8")
        self.assertIn('id="updater-history-button"', html)
        self.assertIn('id="updater-history-picker"', html)
        self.assertNotIn("github.com", html.lower())
        self.assertIn("fetch('/api/updater-history'", events)
        self.assertIn('UPDATER_VERSION = "4"', installer)
        self.assertIn("'installer'", installer)
        self.assertIn('STATS_DATABASE_PATH = Path("/var/lib/solar-inverter-dashboard/stats.sqlite3")', installer)
        self.assertIn('LEGACY_STATS_DATABASE_PATH = APPLICATION_ROOT / "solar_invertor_web_stats.sqlite3"', installer)
        self.assertIn('UPDATER_RECEIPT_PATH = APPLICATION_ROOT / "updater_history.json"', installer)
        self.assertIn('UPDATER_ARCHIVE_DIR = APPLICATION_ROOT / "updater_archives"', installer)
        self.assertIn("def next_updater_version() -> int:", installer)
        self.assertIn("base_version + len(checksums)", installer)
        self.assertIn("legacy_rows", installer)
        self.assertIn("WHERE NOT EXISTS", installer)
        self.assertIn('UPDATER_RECEIPT_PATH = PROJECT_ROOT / "updater_history.json"', runtime)
        self.assertIn('VERSION_URL = "http://127.0.0.1:8080/api/version"', installer)
        self.assertIn("def dashboard_asset_version(payload_root: Path) -> str:", installer)
        self.assertIn("def verify_installed_payload(payload_root: Path) -> None:", installer)
        self.assertIn("def wait_for_health(expected_version: str) -> None:", installer)
        self.assertIn("running_version == expected_version", installer)
        self.assertIn("wait_for_health(expected_version)", installer)
        self.assertIn('request_path == "/api/updater-history/download"', server_source)
        self.assertIn('"Content-Disposition"', server_source)
        self.assertIn("encodeURIComponent(item.archive_file)", events)
        self.assertIn("receipt.get(\"installations\", [])", runtime)
        self.assertIn("WHERE source = 'installer'", runtime)

    def test_installer_migrates_history_to_the_service_database(self) -> None:
        import sqlite3
        import tempfile
        import os
        from contextlib import closing
        from types import SimpleNamespace

        installer = runpy.run_path(str(ROOT / "deploy" / "update_bundle_src" / "__main__.py"))
        record = installer["record_installed_version"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy_path = root / "opt" / "solar_invertor_web_stats.sqlite3"
            service_path = root / "var" / "stats.sqlite3"
            receipt_path = root / "opt" / "updater_history.json"
            archive_dir = root / "opt" / "updater_archives"
            bundle_path = root / "solar-dashboard-update.pyz"
            legacy_path.parent.mkdir(parents=True)
            bundle_path.write_bytes(b"updater-four-test")
            service_path.parent.mkdir(parents=True)
            with closing(sqlite3.connect(service_path)) as connection:
                connection.execute(
                    """
                    CREATE TABLE updater_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commit_hash TEXT NOT NULL,
                        source TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO updater_versions (commit_hash, source, created_at)
                    VALUES ('old-local-build', 'local', '2026-08-08 11:00:00')
                    """
                )
                connection.commit()
            with closing(sqlite3.connect(legacy_path)) as connection:
                connection.execute(
                    """
                    CREATE TABLE updater_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commit_hash TEXT NOT NULL, commit_message TEXT,
                        commit_date TEXT, source TEXT NOT NULL,
                        bundle_path TEXT, build_output TEXT,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO updater_versions
                        (commit_hash, commit_message, commit_date, source,
                         bundle_path, build_output, created_at)
                    VALUES ('updater-4', 'Updater 4', '2026-08-08 12:00:00',
                            'installer', 'old.pyz', 'SHA-256 OLD', '2026-08-08 12:00:00')
                    """
                )
                connection.commit()
            record.__globals__.update({
                "STATS_DATABASE_PATH": service_path,
                "LEGACY_STATS_DATABASE_PATH": legacy_path,
                "UPDATER_RECEIPT_PATH": receipt_path,
                "UPDATER_ARCHIVE_DIR": archive_dir,
                "archive_path": lambda: bundle_path,
                "os": SimpleNamespace(
                    getpid=os.getpid, chmod=os.chmod, chown=lambda *_: None,
                    replace=os.replace,
                ),
            })
            record(1000, 1000, "abc123def456")
            with closing(sqlite3.connect(service_path)) as connection:
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(updater_versions)")
                }
                rows = connection.execute(
                    "SELECT commit_hash, source, build_output FROM updater_versions ORDER BY id"
                ).fetchall()
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            archive_exists = (archive_dir / "solar-dashboard-updater-4-abc123def456.pyz").is_file()
        self.assertIn("build_output", columns)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0], ("old-local-build", "local", None))
        self.assertEqual(rows[1], ("updater-4", "installer", "SHA-256 OLD"))
        self.assertEqual(rows[2][0:2], ("updater-4-abc123def456", "installer"))
        self.assertRegex(rows[2][2], r"^SHA-256 [0-9A-F]{64}$")
        self.assertEqual(receipt["schema"], 1)
        self.assertEqual(receipt["installations"][0]["version"], "4")
        self.assertEqual(receipt["installations"][0]["dashboard_version"], "abc123def456")
        self.assertEqual(receipt["installations"][0]["checksum"], rows[2][2])
        self.assertTrue(archive_exists)

    def test_updater_history_uses_receipt_when_sqlite_history_is_missing(self) -> None:
        import tempfile
        from solar_inverter.services.inverter_service_runtime import get_updater_history

        globals_ = get_updater_history.__globals__
        original_database = globals_["STATS_DB_PATH"]
        original_receipt = globals_["UPDATER_RECEIPT_PATH"]
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                receipt_path = root / "updater_history.json"
                receipt_path.write_text(json.dumps({
                    "schema": 1,
                    "installations": [{
                        "version": "4", "checksum": "SHA-256 RECEIPT",
                        "installed_at": "2026-08-08 14:00:00",
                    }],
                }), encoding="utf-8")
                globals_["STATS_DB_PATH"] = root / "empty.sqlite3"
                globals_["UPDATER_RECEIPT_PATH"] = receipt_path
                history = get_updater_history()
        finally:
            globals_["STATS_DB_PATH"] = original_database
            globals_["UPDATER_RECEIPT_PATH"] = original_receipt
        self.assertEqual(history, [{
            "id": "receipt-0", "version": "4",
            "dashboard_version": "",
            "checksum": "SHA-256 RECEIPT", "installed_at": "2026-08-08 14:00:00",
            "archive_file": "", "download_available": False,
        }])

    def test_updater_history_numbers_releases_and_exposes_archived_bundle(self) -> None:
        import tempfile
        from solar_inverter.services.inverter_service_runtime import get_updater_archive, get_updater_history

        globals_ = get_updater_history.__globals__
        originals = {name: globals_[name] for name in (
            "STATS_DB_PATH", "UPDATER_RECEIPT_PATH", "UPDATER_ARCHIVE_DIR",
        )}
        try:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                archive_dir = root / "updater_archives"
                archive_dir.mkdir()
                archive_name = "solar-dashboard-updater-6-newbuild.pyz"
                (archive_dir / archive_name).write_bytes(b"latest updater")
                receipt_path = root / "updater_history.json"
                receipt_path.write_text(json.dumps({"installations": [
                    {"version": "4", "checksum": "SHA-256 A", "installed_at": "2026-08-08 14:00:00"},
                    {"version": "4", "checksum": "SHA-256 B", "installed_at": "2026-08-08 15:00:00"},
                    {"version": "6", "dashboard_version": "newbuild", "checksum": "SHA-256 C",
                     "installed_at": "2026-08-08 16:00:00", "bundle": archive_name},
                ]}), encoding="utf-8")
                globals_.update({
                    "STATS_DB_PATH": root / "empty.sqlite3",
                    "UPDATER_RECEIPT_PATH": receipt_path,
                    "UPDATER_ARCHIVE_DIR": archive_dir,
                })
                history = get_updater_history()
                downloadable = get_updater_archive(archive_name)
                traversal = get_updater_archive("../" + archive_name)
        finally:
            globals_.update(originals)
        self.assertEqual([item["version"] for item in history], ["6", "5", "4"])
        self.assertTrue(history[0]["download_available"])
        self.assertEqual(history[0]["archive_file"], archive_name)
        self.assertFalse(history[1]["download_available"])
        self.assertEqual(downloadable, archive_dir / archive_name)
        self.assertIsNone(traversal)

    def test_register_metadata_matches_ttn_v131_units_and_scaling(self) -> None:
        from solar_inverter.services.inverter_service_core import REGISTER_CONFIG, normalize

        expected = {
            84: (1.0, "W", True),
            88: (1.0, "W", False),
            92: (1.0, "W", False),
            93: (1.0, "VA", False),
            94: (0.1, "%", False),
            130: (0.1, "A", True),
            133: (0.1, "%", False),
            148: (1.0, "%", False),
            149: (1.0, "W", False),
            150: (1.0, "W", False),
            404: (0.1, "V", True),
            413: (0.1, "A", True),
            414: (0.01, "%", True),
            436: (1.0, "W", True),
            437: (1.0, "", False),
            801: (1.0, "%", False),
        }
        for register, metadata in expected.items():
            with self.subTest(register=register):
                self.assertEqual(REGISTER_CONFIG[register][1:4], metadata)
        self.assertEqual(normalize(81, 2300)[3], 230.0)
        self.assertEqual(normalize(82, 1235)[3], 12.35)
        self.assertEqual(normalize(95, 65536 - 123)[3], -123.0)
        self.assertEqual(normalize(130, 65536 - 180)[3], 18.0)

    def test_ttn_12ku_u30_embedded_workbook_profile(self) -> None:
        from solar_inverter.services.inverter_service_core import (
            FAST_BLOCKS,
            KNOWN_REGISTERS,
            REGISTER_CONFIG,
        )
        from solar_inverter.services.register_profile_12ku import REGISTER_BY_NUMBER, REGISTER_PROFILE

        self.assertEqual(len(REGISTER_PROFILE), 696)
        self.assertEqual(KNOWN_REGISTERS, [row[0] for row in REGISTER_PROFILE])
        self.assertEqual(REGISTER_BY_NUMBER[58][2], "Model ID / Protocol ID B")
        self.assertEqual(REGISTER_BY_NUMBER[16651][5:7], (0.1, "V"))
        self.assertEqual(REGISTER_CONFIG[142][1:3], (0.01, "Ah"))
        self.assertEqual(REGISTER_CONFIG[143][1:3], (0.01, "Ah"))
        self.assertEqual(REGISTER_CONFIG[157][1:3], (0.01, "kWh"))
        self.assertEqual(REGISTER_CONFIG[187][1:3], (0.01, "kWh"))
        self.assertEqual(
            REGISTER_BY_NUMBER[68][2:5],
            ("Состояние силовых клемм", "только чтение", "uint16_t"),
        )
        self.assertEqual(REGISTER_BY_NUMBER[70][2], "Статус топологии / single")
        self.assertEqual(REGISTER_BY_NUMBER[437][2], "Reserved после мощности сети A")
        self.assertIn((1, 120), FAST_BLOCKS)

    def test_12ku_cards_prioritize_measured_output_voltage(self) -> None:
        from solar_inverter.services.inverter_service_core import METER_DEFINITIONS

        output_voltage = next(item for item in METER_DEFINITIONS if item[0] == 537)
        self.assertEqual(output_voltage[1], [89])
        lcd = (WEB_ROOT / "scripts" / "lcd.js").read_text(encoding="utf-8")
        flow = (WEB_ROOT / "scripts" / "energy-flow.js").read_text(encoding="utf-8")
        self.assertIn("numberValue([537, 89])", lcd)
        self.assertIn("firstRegister([537, 89])", flow)
        self.assertNotIn("numberValue([84, 437, 436])", lcd)

    def test_build_and_installer_payload_manifests_match(self) -> None:
        build = runpy.run_path(str(ROOT / "deploy" / "build_update_bundle.py"))
        installer = runpy.run_path(str(ROOT / "deploy" / "update_bundle_src" / "__main__.py"))
        build_payload = set(build["PAYLOAD_FILES"])
        installed_payload = set(installer["PAYLOAD_FILES"])
        installed_payload.add(installer["SERVICE_PAYLOAD"])
        self.assertEqual(build_payload, installed_payload)
        for relative_name in build_payload:
            self.assertTrue((ROOT / relative_name).is_file(), relative_name)

    def test_first_party_app_files_do_not_exceed_900_lines(self) -> None:
        source_extensions = {".py", ".js", ".css", ".html"}
        source_roots = (ROOT / "solar_inverter", ROOT / "deploy")
        source_files = [ROOT / "solar_invertor_web.py"]
        for source_root in source_roots:
            source_files.extend(
                path
                for path in source_root.rglob("*")
                if path.is_file()
                and path.suffix in source_extensions
                and "__pycache__" not in path.parts
            )

        oversized = {
            str(path.relative_to(ROOT)): len(path.read_text(encoding="utf-8").splitlines())
            for path in source_files
            if len(path.read_text(encoding="utf-8").splitlines()) > 900
        }
        self.assertEqual(oversized, {})


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript renderer tests")
class DashboardRendererTests(unittest.TestCase):
    def test_demo_register_values_round_trip_like_live_v131_values(self) -> None:
        chart_path = WEB_ROOT / "scripts" / "charts.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            const source = fs.readFileSync(process.argv[1], 'utf8');
            const start = source.indexOf('function demoRawValue');
            const end = source.indexOf('function continuousDemoChartValue', start);
            eval(source.slice(start, end));
            const samples = [
              {register:81, scale:.1, signed:false, requested:230.04},
              {register:82, scale:.01, signed:false, requested:12.345},
              {register:95, scale:1, signed:true, requested:-123},
              {register:130, scale:.1, signed:true, requested:18.04},
              {register:130, scale:.1, signed:true, requested:-18.04},
              {register:134, scale:1, signed:false, requested:-936},
              {register:67, scale:1, signed:false, requested:4.7},
              {register:94, scale:.1, signed:false, requested:24.94}
            ];
            console.log(JSON.stringify(samples.map(item => demoRegisterReading(item, item.requested))));
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(chart_path)],
            check=True, capture_output=True, text=True,
        )
        readings = json.loads(result.stdout)
        self.assertEqual(readings, [
            {"raw": 2300, "value": 230, "display": "230.0", "available": True},
            {"raw": 1235, "value": 12.35, "display": "12.35", "available": True},
            {"raw": 65413, "value": -123, "display": "-123", "available": True},
            {"raw": 65356, "value": 18, "display": "18.0", "available": True},
            {"raw": 180, "value": -18, "display": "-18.0", "available": True},
            {"raw": 936, "value": -936, "display": "-936", "available": True},
            {"raw": 5, "value": 5, "display": "5", "available": True},
            {"raw": 249, "value": 24.9, "display": "24.9", "available": True},
        ])
        browser_source = script_source("app.js", "charts.js", "energy-flow.js", "lcd.js")
        self.assertIn("function registerNumericValue(register)", browser_source)
        self.assertGreaterEqual(browser_source.count("registerNumericValue("), 18)

    def test_demo_r67_to_r70_words_describe_each_energy_route(self) -> None:
        chart_path = WEB_ROOT / "scripts" / "charts.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            const source = fs.readFileSync(process.argv[1], 'utf8');
            const start = source.indexOf('function interpolate');
            const end = source.indexOf('function demoSolarEnergySummary', start);
            eval(source.slice(start, end));
            console.log(JSON.stringify([10, 30, 50, 70, 90, 110].map(second => {
              const values = realisticDemoScenario(second).values;
              return [values.get(67), values.get(68), values.get(69), values.get(70), values.get(322), values.get(325), values.get(133), values.get(139), values.get(339)];
            })));
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(chart_path)],
            check=True, capture_output=True, text=True,
        )
        frames = json.loads(result.stdout)
        self.assertEqual([frame[0] for frame in frames], [4, 3, 5, 4, 6, 4])
        self.assertEqual([frame[3] for frame in frames], [0, 1, 2, 3, 4, 0])
        self.assertEqual([frame[4] for frame in frames], [0, 1, 2, 3, 4, 0])
        self.assertEqual([frame[5] for frame in frames], [4, 3, 5, 4, 6, 4])
        expected_r69 = [624, 611, 768, 592, 588, 848]
        self.assertEqual([frame[2] for frame in frames], expected_r69)
        # Every frame has a normal main output in R68; source terminals vary by route.
        self.assertTrue(all(((frame[1] >> 6) & 3) == 1 for frame in frames))
        self.assertEqual([frame[1] & 3 for frame in frames], [0, 2, 0, 0, 0, 0])
        self.assertEqual([(frame[1] >> 2) & 3 for frame in frames], [0, 0, 0, 0, 2, 0])
        self.assertEqual([frames[index][6:] for index in (3, 4)], [[100, 100, 100], [100, 100, 100]])

    def test_full_r68_battery_state_forces_a_complete_soc_display(self) -> None:
        flow = (WEB_ROOT / "scripts" / "energy-flow.js").read_text(encoding="utf-8")
        lcd = (WEB_ROOT / "scripts" / "lcd.js").read_text(encoding="utf-8")
        self.assertIn("firstRegister([133, 139, 339, 407])", flow)
        self.assertIn("function effectiveBatterySoc(measuredSoc, terminalState)", flow)
        self.assertIn("if (terminalState?.battery === 4) return 100", flow)
        self.assertIn("const effectiveSoc = effectiveBatterySoc(batterySoc, terminalState)", flow)
        self.assertIn("batteryLevelKnown ? `${Math.round(batteryLevel)}%` : '—'", flow)
        self.assertIn("numberValue([133, 139, 339, 407])", lcd)
        self.assertIn("const batterySoc = effectiveBatterySoc(measuredBatterySoc, terminalState)", lcd)

    def test_api_battery_soc_uses_r68_full_state_without_mutating_raw_data(self) -> None:
        from solar_inverter.components.web_dashboard import effective_battery_soc

        full_terminal_state = 4 << 8
        self.assertEqual(effective_battery_soc(73.0, full_terminal_state), 100.0)
        self.assertEqual(effective_battery_soc(73.0, 3 << 8), 73.0)
        self.assertEqual(effective_battery_soc(None, full_terminal_state), 100.0)
        self.assertIsNone(effective_battery_soc(None, None))

    def test_lcd_uses_canonical_state_registers_for_connections_and_flow(self) -> None:
        lcd = (WEB_ROOT / "scripts" / "lcd.js").read_text(encoding="utf-8")
        self.assertIn("firstRegister([67, 325])", lcd)
        self.assertIn("firstRegister([69])", lcd)
        self.assertNotIn("firstRegister([68])", lcd)
        self.assertIn("const terminalState = null", lcd)
        self.assertIn("decodeEnergyFlowState(flowStateSource)", lcd)
        self.assertIn("flowState.gridToRectifier || flowState.gridToLoad || flowState.rectifierToGrid", lcd)
        self.assertIn("flowState.inverterToMainOutput || flowState.inverterToSecondaryOutput", lcd)

    def test_all_tabs_use_complete_translation_catalogs(self) -> None:
        translation_path = WEB_ROOT / "scripts" / "translations.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            const source = fs.readFileSync(process.argv[1], 'utf8');
            eval(source + `
              console.log(JSON.stringify({
                ui: Object.fromEntries(
                  Object.entries(UI_TRANSLATIONS).map(([language, values]) =>
                    [language, Object.keys(values)])
                ),
                data: Object.keys(DATA_TRANSLATIONS)
              }));
            `);
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(translation_path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        translation_keys = json.loads(result.stdout)
        catalogs = {language: set(keys) for language, keys in translation_keys["ui"].items()}
        self.assertEqual(catalogs["uk"], catalogs["ru"])
        self.assertEqual(catalogs["uk"], catalogs["en"])

        sources = [(WEB_ROOT / "index.html").read_text(encoding="utf-8")]
        sources.extend(path.read_text(encoding="utf-8") for path in (WEB_ROOT / "scripts").glob("*.js"))
        used_keys: set[str] = set()
        for source in sources:
            used_keys.update(re.findall(r'data-i18n(?:-aria|-placeholder|-title)?="([^"]+)"', source))
            used_keys.update(re.findall(r'data-disabled-reason="([^"]+)"', source))
            used_keys.update(re.findall(r"\bt\(\s*['\"]([^'\"]+)['\"]", source))
        self.assertEqual(used_keys - catalogs["uk"], set())
        localized_literals: set[str] = set()
        for source in sources:
            localized_literals.update(re.findall(
                r"localizeDataText\(\s*['\"]([^'\"]+)['\"]",
                source,
            ))
        self.assertEqual(localized_literals - set(translation_keys["data"]), set())

        api_catalog = json.loads(
            (WEB_ROOT / "data" / "data-translations.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(api_catalog), set(translation_keys["data"]))
        self.assertTrue(all(set(values) == {"ru", "en"} for values in api_catalog.values()))

    def test_demo_populates_fan_for_dashboard_charts_and_lcd_data(self) -> None:
        html_source = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        chart_source = script_source("charts.js", "chart-demo-history.js", "chart-rendering.js")
        flow_source = (WEB_ROOT / "scripts" / "energy-flow.js").read_text(encoding="utf-8")
        lcd_source = (WEB_ROOT / "scripts" / "lcd.js").read_text(encoding="utf-8")
        css_source = dashboard_css()
        self.assertIn("const fanSpeed =", chart_source)
        self.assertIn("second / 120 * 100", chart_source)
        self.assertIn("[801, fanSpeed]", chart_source)
        self.assertIn("renderEnergyFlow(lastData, demoRegisterRows)", chart_source)
        self.assertIn("const demoFanSpeed = registerNumericValue(demoRowsByNumber.get(801))", chart_source)
        self.assertIn("updateInverterFanAnimation(", chart_source)
        self.assertIn("function synchronizeDemoChartDefinitions(scenario)", chart_source)
        self.assertIn("item.displayValue = registerVersionDisplay(matchingRegister", chart_source)
        self.assertIn("registerInterpretation({...matchingRegister, versionDisplay: item.displayValue})", chart_source)
        self.assertIn("item.source = `R${item.register} · ${t('demoMode')}`", chart_source)
        self.assertIn("renderLcd(lastData, demoRegisterRows)", chart_source)
        self.assertIn('id="lcd-inverter-fan-speed"', html_source)
        self.assertIn("const inverterFanSpeedReading = numberValue([801])", lcd_source)
        self.assertIn("setText('#lcd-inverter-fan-speed', reading(inverterFanSpeed, '%', 1))", lcd_source)
        self.assertIn("registerInterpretation(statusRegister) || localizeDataText(statusRegister.display)", lcd_source)
        self.assertIn("const isPercentage = register.unit === '%'", chart_source)
        self.assertIn("isPercentage ? Math.max(0, Math.min(100, value)) : value", chart_source)
        self.assertIn("function seedDemoHistory()", chart_source)
        self.assertIn("const pointCounts = {day: 288, week: 336, month: 360, year: 365, lifetime: 365}", chart_source)
        self.assertIn("const demoWindowSeconds = Number.isFinite(windowSeconds) ? windowSeconds : 315360000", chart_source)
        self.assertNotIn("displaySeconds", chart_source)
        self.assertIn("previousValue + random() * scale * .01", chart_source)
        self.assertIn("Math.max(0, Math.min(100, inverterFanSpeed))", flow_source)
        self.assertIn("reading(normalizedFanSpeed, '%', 1)", flow_source)
        self.assertIn("function updateInverterFanAnimation(fanRow, normalizedSpeed, forceMotion = false)", flow_source)
        self.assertIn("forceMotion || !window.matchMedia", flow_source)
        self.assertIn("const INVERTER_FAN_MAX_ROTATION_MS = 225", flow_source)
        self.assertIn("{duration: INVERTER_FAN_MAX_ROTATION_MS, iterations: Infinity}", flow_source)
        self.assertIn("inverterFanAnimation.updatePlaybackRate(playbackRate)", flow_source)
        self.assertIn("const playbackRate = normalizedSpeed / 100", flow_source)
        self.assertIn("inverterFanAnimation.pause()", flow_source)
        self.assertIn("Array.from(fullLabel).slice(0, 3).join('')", flow_source)
        self.assertIn("element.dataset.sourceIcon = mode.icon", flow_source)
        self.assertIn("element.setAttribute('aria-label', fullLabel)", flow_source)
        self.assertIn("icon: 'grid'", flow_source)
        self.assertIn("icon: 'pv'", flow_source)
        self.assertIn("icon: 'generator'", flow_source)
        self.assertIn("icon: 'battery'", flow_source)
        self.assertIn('.energy-source-icon[data-source-icon="grid"]', css_source)
        self.assertIn('.energy-source-icon[data-source-icon="pv"]::before', css_source)
        self.assertIn('.energy-source-icon[data-source-icon="generator"]', css_source)
        self.assertIn('.energy-source-icon[data-source-icon="battery"]::before', css_source)
        self.assertNotIn("--fan-duration", flow_source)
        self.assertNotIn("var(--fan-duration, 1s)", css_source)
        self.assertIn(".energy-inverter-fan-row.css-animation-fallback.active .energy-inverter-fan-rotor", css_source)
        self.assertIn("transform-box: view-box; transform-origin: 12px 12px", css_source)
        self.assertIn("position: absolute; z-index: 3; left: 6px; top: 58%; bottom: auto", css_source)
        self.assertIn(".energy-inverter .energy-node-value { top: 76% }", css_source)
        self.assertIn("flex-direction: column; width: 60px; max-width: 60px", css_source)
        self.assertIn("flex: 0 0 48px; width: 60px; height: 48px", css_source)
        self.assertIn("left: 50%; right: auto; top: 64%; width: 48%", css_source)
        self.assertIn("row-gap: 10px", css_source)
        self.assertIn("color: #fff; font-size: clamp(18px,5.2vw,22px)", css_source)
        self.assertIn("left: 50%; right: auto; top: 64%; width: 48%; row-gap: 8px", css_source)
        self.assertIn("transform: translateY(-10px)", css_source)
        self.assertIn("transform: translate(-50%,-50%)", css_source)

    def test_lcd_information_pages_use_only_explicit_v131_registers(self) -> None:
        lcd = (WEB_ROOT / "scripts" / "lcd.js").read_text(encoding="utf-8")
        translations = (WEB_ROOT / "scripts" / "translations.js").read_text(encoding="utf-8")
        css_source = "\n".join(
            path.read_text(encoding="utf-8") for path in (WEB_ROOT / "styles").glob("*.css")
        )
        expected = {
            1: (157,), 2: (158,), 3: (137, 138), 4: (140, 139),
            5: (409, 408), 6: (411, 415), 7: (413, 412),
            8: (17, 18, 27, 28), 9: (161, 95), 10: (159, 160),
        }
        for page, registers in expected.items():
            start = lcd.index(f"code: 'P{page}'")
            end_marker = f"code: 'P{page + 1}'" if page < 10 else "code: 'P11'"
            end = lcd.index(end_marker, start)
            block = lcd[start:end]
            for register in registers:
                self.assertRegex(block, rf"(?:numberValue\(\[{register}\]\)|registerLabel\([^\n]*\b{register}\b|versionValue\([^\n]*\b{register}\b|interpretedValue\([^\n]*\b{register}\b)")
        self.assertIn("registerLabel(157, t('dailyPvEnergy'))", lcd)
        self.assertNotIn("registerLabel(403, t('bmsConnection'))", lcd[lcd.index("code: 'P1'"):lcd.index("code: 'P11'")])
        self.assertIn("].slice(0, 11);", lcd)
        app = (WEB_ROOT / "scripts" / "app.js").read_text(encoding="utf-8")
        runtime = (ROOT / "solar_inverter" / "services" / "inverter_service_runtime.py").read_text(encoding="utf-8")
        self.assertIn("const lcdInformationPageCount = 10", app)
        self.assertIn('re.fullmatch(r"P(?:[1-9]|10)", clean_page)', runtime)
        self.assertNotRegex(lcd + translations, r"(?i)local(?:ьной|ьної)? SQLite")
        self.assertIn("justify-items: center; color: #fff; text-align: center", css_source)
        self.assertIn("display: grid; place-items: center; width: 100%; gap: 0", css_source)
        self.assertIn("color: #fff; font-size: 18px; font-weight: 950", css_source)
        self.assertIn("justify-items: center; text-align: center; font-size: 14px", css_source)
        self.assertIn(".lcd-readouts { grid-template-columns: repeat(2,minmax(0,1fr))", css_source)
        self.assertIn(".gauge-picker { width: calc(100% - 16px)", css_source)

    def test_lcd_main_screen_matches_device_layout_and_live_v131_values(self) -> None:
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        lcd = (WEB_ROOT / "scripts" / "lcd.js").read_text(encoding="utf-8")
        css_source = dashboard_css()
        for element_id in (
            "lcd-device-display", "lcd-battery-voltage", "lcd-charge-voltage",
            "lcd-battery-current", "lcd-soc", "lcd-grid-voltage", "lcd-frequency",
            "lcd-ac2-voltage", "lcd-ac2-frequency", "lcd-output-voltage",
            "lcd-output-frequency", "lcd-pv-voltage", "lcd-pv-current",
            "lcd-pv-power", "lcd-pv-day-energy",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn("container-type: inline-size; width: 100%; min-width: 0; aspect-ratio: 1.65", css_source)
        self.assertIn(".lcd-battery-scale", css_source)
        for symbol_id in (
            "lcd-icon-source-square", "lcd-icon-source-wide", "lcd-icon-arrow-long",
            "lcd-icon-arrow-compact", "lcd-icon-solar", "lcd-icon-sun",
            "lcd-icon-battery-vertical", "lcd-icon-battery-horizontal",
        ):
            self.assertIn(f'id="{symbol_id}"', html)
        self.assertIn(".lcd-battery-level-fill", css_source)
        self.assertIn(".lcd-digits-extra-long", css_source)
        self.assertIn("width: 19%; gap: .55cqw; overflow: hidden", css_source)
        self.assertIn(".lcd-panel { width: 100%; min-width: 0", css_source)
        self.assertIn("displayValue.length >= 8", lcd)
        self.assertIn(".lcd-column-input", css_source)
        self.assertIn(".lcd-column-output", css_source)
        self.assertIn(".lcd-column-pv", css_source)
        self.assertIn("const outputVoltage = numberValue([537, 89])", lcd)
        self.assertIn("const outputFrequency = numberValue([91, 538])", lcd)
        self.assertIn("const pvVoltage = numberValue([609])", lcd)
        self.assertIn("const pvCurrent = sumValues([152, 155])", lcd)
        self.assertIn("const pvPower = numberValue([161]) ?? sumValues([153, 156])", lcd)
        self.assertIn("const dailyPvEnergy = numberValue([157])", lcd)
        self.assertIn("setMeasure('#lcd-pv-day-energy', dailyPvEnergy)", lcd)
        self.assertIn("--lcd-soc", lcd)

    def test_fan_animation_keeps_one_timeline_across_data_updates(self) -> None:
        flow_path = WEB_ROOT / "scripts" / "energy-flow.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            global.window = {matchMedia: () => ({matches: false})};
            const classes = new Set();
            let animateCalls = 0;
            let playCalls = 0;
            let pauseCalls = 0;
            const rateUpdates = [];
            const animation = {
              playState: 'running', playbackRate: 1,
              pause() { pauseCalls += 1; this.playState = 'paused'; },
              play() { playCalls += 1; this.playState = 'running'; },
              updatePlaybackRate(value) { rateUpdates.push(value); this.playbackRate = value; },
              cancel() {}
            };
            const rotor = {
              style: {},
              animate() { animateCalls += 1; return animation; }
            };
            const row = {
              querySelector: () => rotor,
              classList: {
                add: name => classes.add(name),
                remove: name => classes.delete(name),
                toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); }
              }
            };
            const source = fs.readFileSync(process.argv[1], 'utf8');
            eval(source + `
              updateInverterFanAnimation(row, 50);
              updateInverterFanAnimation(row, 80);
              updateInverterFanAnimation(row, 0);
              updateInverterFanAnimation(row, 25);
              console.log(JSON.stringify({
                animateCalls, playCalls, pauseCalls, rateUpdates,
                playbackRate: animation.playbackRate,
                active: classes.has('active'),
                fallback: classes.has('css-animation-fallback')
              }));
            `);
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(flow_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            json.loads(result.stdout),
            {
                "animateCalls": 1,
                "playCalls": 2,
                "pauseCalls": 2,
                "rateUpdates": [0.8],
                "playbackRate": 0.25,
                "active": True,
                "fallback": False,
            },
        )

    def test_energy_and_gauge_renderers(self) -> None:
        renderer_path = WEB_ROOT / "scripts" / "renderers.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            const elements = new Map();
            function element(selector) {
              const value = {
                textContent: '', hidden: false, active: false,
                classList: {toggle(name, enabled) { if (name === 'active') value.active = enabled; }}
              };
              elements.set(selector, value);
              return value;
            }
            global.document = {querySelector: selector => elements.get(selector) || null};
            element('#card'); element('#value'); element('#values'); element('#direction');
            const source = fs.readFileSync(process.argv[1], 'utf8');
            eval(source + `
              DashboardRenderers.energyCard({
                nodeSelector: '#card', active: true,
                values: {'#value': '52.4 V'},
                valuesSelector: '#values', valuesVisible: false,
                directionSelector: '#direction', direction: 'CHARGING'
              });
              const meter = {key:'battery', colour:'#34d399', register:129, unit:'V', detail:'R129', interpretation:'PV mode'};
              const gauge = DashboardRenderers.gaugeCard({
                meter, label:'Battery', showSpeedometer:false, scale:'',
                translations:{drag:'Drag', remove:'Remove'}
              });
              console.log(JSON.stringify({
                active: elements.get('#card').active,
                value: elements.get('#value').textContent,
                hidden: elements.get('#values').hidden,
                direction: elements.get('#direction').textContent,
                noSpeedometer: gauge.includes('no-speedometer') && !gauge.includes('<svg'),
                register: gauge.includes('R129'),
                interpretation: gauge.includes('PV mode')
              }));
            `);
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(renderer_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            json.loads(result.stdout),
            {
                "active": True,
                "value": "52.4 V",
                "hidden": True,
                "direction": "CHARGING",
                "noSpeedometer": True,
                "register": True,
                "interpretation": True,
            },
        )

    def test_ttn_v131_state_and_bit_field_interpretations(self) -> None:
        interpretation_path = WEB_ROOT / "scripts" / "interpretations.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            let currentLanguage = 'en';
            const source = fs.readFileSync(process.argv[1], 'utf8');
            eval(source + `
              const versionRegisters = [
                {register:17, raw:1, display:'1', available:true},
                {register:18, raw:31, display:'31', available:true},
                {register:27, raw:1, display:'1', available:true},
                {register:28, raw:31, display:'31', available:true}
              ];
              const englishState = registerInterpretation({register:67, raw:4, available:true, unit:'', name:'State'});
              currentLanguage = 'uk';
              const ukrainianState = registerInterpretation({register:67, raw:4, available:true, unit:'', name:'State'});
              currentLanguage = 'ru';
              const russianState = registerInterpretation({register:67, raw:4, available:true, unit:'', name:'State'});
              currentLanguage = 'en';
              console.log(JSON.stringify({
                pvMode: englishState,
                ukrainianState,
                russianState,
                serialWord: registerInterpretation({register:3, raw:18766, available:true, unit:'', name:'SN'}),
                serialPadding: registerInterpretation({register:10, raw:0, available:true, unit:'', name:'SN'}),
                protocolDisplay: registerVersionDisplay(versionRegisters[0], versionRegisters),
                controlSoftwareDisplay: registerVersionDisplay(versionRegisters[3], versionRegisters),
                protocolMajor: registerInterpretation({register:17, raw:1, available:true, unit:'', name:'Version', versionDisplay:'V1.3'}),
                controlSoftwareMinor: registerInterpretation({register:28, raw:31, available:true, unit:'', name:'Version', versionDisplay:'V1.3'}),
                bmsCan: registerInterpretation({register:66, raw:1, available:true, unit:'', name:'Status'}),
                bmsPacket: registerInterpretation({register:402, raw:37, available:true, unit:'', name:'Packet ID'}),
                bmsDebugLocked: registerInterpretation({register:403, raw:2, available:true, unit:'', name:'Status'}),
                energyFlow: registerInterpretation({register:69, raw:(1 << 4) | (1 << 9), available:true, unit:'', name:'Flow status'}),
                faultsClear: registerInterpretation({register:71, raw:0, available:true, unit:'', name:'Fault'}),
                faults: registerInterpretation({register:71, raw:(1 << 1) | (1 << 4), available:true, unit:'', name:'Fault'}),
                fanStalled: registerInterpretation({register:802, raw:1, available:true, unit:'', name:'Fan status'}),
                unavailable: registerInterpretation({register:67, raw:null, available:false, unit:'', name:'State'})
              }));
            `);
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(interpretation_path)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(
            json.loads(result.stdout),
            {
                "pvMode": "PV mode",
                "ukrainianState": "Робота від PV",
                "russianState": "Работа от PV",
                "serialWord": "SN word R3: 0x494E → “IN”; each word contains up to two ASCII characters",
                "serialPadding": "SN word R10: 0x0000 is empty padding or the end of the identifier",
                "protocolDisplay": "V1.3",
                "controlSoftwareDisplay": "V1.3",
                "protocolMajor": "protocol version: major component = 1; decoded display V1.3",
                "controlSoftwareMinor": "control-board software version: minor component = 31; decoded display V1.3",
                "bmsCan": "ID locked through CAN",
                "bmsPacket": "BMS packet ID: 37",
                "bmsDebugLocked": "BMS ID locked",
                "energyFlow": "PV \N{RIGHTWARDS ARROW} rectifier; Inverter \N{RIGHTWARDS ARROW} main output",
                "faultsClear": "No active faults",
                "faults": "Bus overvoltage; Overtemperature",
                "fanStalled": "Fan stalled or not rotating",
                "unavailable": "",
            },
        )

    def test_speedometers_are_only_used_for_measurable_values(self) -> None:
        gauge_path = WEB_ROOT / "scripts" / "gauges.js"
        probe = textwrap.dedent(
            """
            const fs = require('fs');
            const source = fs.readFileSync(process.argv[1], 'utf8');
            eval(source + `
              console.log(JSON.stringify({
                zeroVolts: showsSpeedometer({value: 0, unit: 'V'}),
                fanPercent: showsSpeedometer({value: 62, unit: '%'}),
                energy: showsSpeedometer({value: 12.5, unit: 'kWh'}),
                inverterStatus: showsSpeedometer({value: 3, unit: '', label: 'Status'}),
                batteryMode: showsSpeedometer({value: 2, unit: '', label: 'Battery mode'}),
                flags: showsSpeedometer({value: 255, unit: '', label: 'Flags'}),
                unavailable: showsSpeedometer({value: NaN, unit: 'A'})
              }));
            `);
            """
        )
        result = subprocess.run(
            [shutil.which("node") or "node", "-e", probe, str(gauge_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            json.loads(result.stdout),
            {
                "zeroVolts": True,
                "fanPercent": True,
                "energy": True,
                "inverterStatus": False,
                "batteryMode": False,
                "flags": False,
                "unavailable": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
