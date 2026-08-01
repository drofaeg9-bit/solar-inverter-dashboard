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
        charts = script_source("charts.js", "chart-rendering.js")
        app = script_source("app.js", "app-events.js")
        self.assertNotIn("backdrop-filter: blur(18px)", css)
        self.assertIn("scrollbar-gutter: stable", css)
        self.assertIn("position: fixed; z-index: 1000", css)
        self.assertIn("gaugeSelectionRenderPending", charts)
        self.assertIn("requestAnimationFrame(() => window.setTimeout", charts)
        self.assertIn("requestAnimationFrame(() => window.setTimeout(drawAllCharts, 0))", app)
        self.assertIn("window.requestIdleCallback(renderPendingRegisters, {timeout: 750})", app)
        self.assertIn("content-visibility: auto", css)
        self.assertNotIn("canvas.clientWidth", charts)
        self.assertNotIn("canvas.clientHeight", charts)
        self.assertNotIn("canvas.getBoundingClientRect()", charts)
        self.assertIn("new ResizeObserver", charts)
        self.assertIn("new IntersectionObserver", charts)
        self.assertIn("const jobs = [...visibleChartCanvases]", charts)
        self.assertIn("context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)", charts)
        self.assertIn("context.lineWidth = 1.5", charts)
        self.assertIn("context.lineWidth = 3", charts)
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
        self.assertIn("const configuredSeconds = (requestIntervals[data.poll_rate_index] ?? 1000) / 1000", app)
        self.assertIn("renderCycleStatus(lastData)", app)
        self.assertIn("const VALUE_LIST_RENDER_LIMIT = 80", charts)
        self.assertIn("const CHARTS_PER_PAGE = 12", charts)
        self.assertIn("selected.slice(pageStart, pageStart + CHARTS_PER_PAGE)", charts)
        self.assertIn("function scheduleChartsViewRender()", charts)
        self.assertIn("scheduleChartsViewRender();", app)
        self.assertIn("data-chart-page", charts)
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('role="tabpanel" aria-labelledby="dashboard-tab"', html)
        self.assertIn('aria-controls="charts-view"', html)
        self.assertIn('data-i18n="lcdUpKey"', html)
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
        self.assertIn("const colour = dashboardGaugeColour(item)", charts)
        self.assertIn("themeStyles.getPropertyValue(customProperty).trim()", charts)
        self.assertIn("--flow-generator-colour: #fb923c", css)
        self.assertIn("--flow-generator-colour: #985a2e", css)

    def test_flow_connectors_stay_behind_every_card(self) -> None:
        css = dashboard_css()
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("display: grid; isolation: isolate", css)
        self.assertIn("position: relative; z-index: 1; align-self: stretch", css)
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
        self.assertEqual(WEB_DASHBOARD.count("<script defer src="), len(SCRIPT_NAMES))
        self.assertNotIn("const UI_TRANSLATIONS", WEB_DASHBOARD)
        self.assertNotIn("function renderEnergyFlow", WEB_DASHBOARD)

    def test_static_assets_use_compression_and_long_lived_caching(self) -> None:
        server = (ROOT / "solar_inverter" / "components" / "web_dashboard.py").read_text(encoding="utf-8")
        css = dashboard_css()
        self.assertIn('gzip.compress(body, compresslevel=5, mtime=0)', server)
        self.assertIn('cache_control="public, max-age=31536000, immutable"', server)
        self.assertIn('cache_control="private, max-age=0, must-revalidate"', server)
        self.assertIn("/assets/generator-mask.png?v=__ASSET_VERSION__", css)
        self.assertLess((ROOT / "generator-mask.png").stat().st_size, 20_000)

    def test_poll_timing_reports_real_cycles_and_accounts_for_postprocessing(self) -> None:
        service = inverter_service_source()
        server = (ROOT / "solar_inverter" / "components" / "web_dashboard.py").read_text(encoding="utf-8")
        self.assertIn('"read_seconds": 0.0', service)
        self.assertIn("cycle_duration = round(cycle_interval or read_duration, 2)", service)
        self.assertIn("cycle_work_duration = time.monotonic() - started", service)
        self.assertIn("poll_rate - cycle_work_duration", service)
        self.assertIn('"read_seconds": snapshot["read_seconds"]', server)

    def test_static_route_map_contains_every_referenced_asset(self) -> None:
        from solar_inverter.components.web_dashboard import DASHBOARD_STATIC_PATHS

        expected = {"/static/styles/dashboard.css", "/static/styles/dashboard-responsive.css"} | {
            f"/static/scripts/{name}" for name in SCRIPT_NAMES
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

    def test_build_and_installer_payload_manifests_match(self) -> None:
        build = runpy.run_path(str(ROOT / "deploy" / "build_update_bundle.py"))
        installer = runpy.run_path(str(ROOT / "deploy" / "update_bundle_src" / "__main__.py"))
        build_payload = set(build["PAYLOAD_FILES"])
        installed_payload = set(installer["PAYLOAD_FILES"])
        installed_payload.add(installer["SERVICE_PAYLOAD"])
        self.assertEqual(build_payload, installed_payload)
        for relative_name in build_payload:
            self.assertTrue((ROOT / relative_name).is_file(), relative_name)

    def test_first_party_app_files_do_not_exceed_800_lines(self) -> None:
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
            if len(path.read_text(encoding="utf-8").splitlines()) > 800
        }
        self.assertEqual(oversized, {})


@unittest.skipUnless(shutil.which("node"), "Node.js is required for JavaScript renderer tests")
class DashboardRendererTests(unittest.TestCase):
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

    def test_demo_populates_fan_for_dashboard_charts_and_lcd_data(self) -> None:
        html_source = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        chart_source = script_source("charts.js", "chart-rendering.js")
        flow_source = (WEB_ROOT / "scripts" / "energy-flow.js").read_text(encoding="utf-8")
        lcd_source = (WEB_ROOT / "scripts" / "lcd.js").read_text(encoding="utf-8")
        css_source = dashboard_css()
        self.assertIn("const fanSpeed =", chart_source)
        self.assertIn("second / chartWindowSeconds * 100", chart_source)
        self.assertIn("[801, fanSpeed]", chart_source)
        self.assertIn("renderEnergyFlow(lastData, demoRegisterRows)", chart_source)
        self.assertIn("const demoFanSpeed = Number(scenario.values.get(801))", chart_source)
        self.assertIn("updateInverterFanAnimation(", chart_source)
        self.assertIn("const synchronizeDemoDefinitions = scenario =>", chart_source)
        self.assertIn("item.interpretation = demoRegister ? registerInterpretation(demoRegister) : ''", chart_source)
        self.assertIn("item.source = `R${item.register} · ${t('demoMode')}`", chart_source)
        self.assertIn("renderLcd(lastData, demoRegisterRows)", chart_source)
        self.assertIn('id="lcd-inverter-fan-speed"', html_source)
        self.assertIn("const inverterFanSpeedReading = numberValue([801])", lcd_source)
        self.assertIn("setText('#lcd-inverter-fan-speed', reading(inverterFanSpeed, '%', 1))", lcd_source)
        self.assertIn("registerInterpretation(statusRegister) || localizeDataText(statusRegister.display)", lcd_source)
        self.assertIn("const isPercentage = register.unit === '%'", chart_source)
        self.assertIn("const chartValue = isPercentage ? Math.max(0, Math.min(100, value)) : value", chart_source)
        self.assertIn("const hasConfiguredRange =", chart_source)
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
        self.assertIn("setText(selector, displayLabel)", flow_source)
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
        self.assertIn("justify-items: center; color: #fff; text-align: center", css_source)
        self.assertIn("display: grid; place-items: center; width: 100%; gap: 0", css_source)
        self.assertIn("color: #fff; font-size: 18px; font-weight: 950", css_source)
        self.assertIn("justify-items: center; text-align: center; font-size: 14px", css_source)
        self.assertIn(".lcd-readouts { grid-template-columns: repeat(2,minmax(0,1fr))", css_source)
        self.assertIn(".gauge-picker { width: calc(100% - 16px)", css_source)

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
                protocolMajor: registerInterpretation({register:17, raw:1, available:true, unit:'', name:'Version'}),
                controlSoftwareMinor: registerInterpretation({register:28, raw:31, available:true, unit:'', name:'Version'}),
                bmsCan: registerInterpretation({register:66, raw:1, available:true, unit:'', name:'Status'}),
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
                "protocolMajor": "protocol version: major component = 1; R17 and R18 together form V[R17].[R18]",
                "controlSoftwareMinor": "control-board software version: minor component = 31; R27 and R28 together form V[R27].[R28]",
                "bmsCan": "ID locked through CAN",
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
