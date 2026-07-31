from __future__ import annotations

WEB_DASHBOARD = r"""<!doctype html>
<html lang="uk" class="booting">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <link rel="icon" type="image/png" sizes="any" href="/favicon.png">
  <title>Solar Inverter Web</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #07111f;
      --panel: rgba(15, 28, 46, .76);
      --line: rgba(148, 163, 184, .14);
      --text: #f1f5f9;
      --muted: #8ea0b8;
      --cyan: #22d3ee;
      --blue: #38bdf8;
      --green: #34d399;
      --amber: #fbbf24;
      --red: #fb7185;
      --control: rgba(10, 22, 37, .76);
      --card-start: rgba(21, 38, 59, .86);
      --card-end: rgba(9, 20, 34, .82);
      --table-head: #101f32;
      --gauge-track: rgba(148,163,184,.14);
      --gauge-tick: rgba(226,232,240,.42);
      --gauge-major: rgba(241,245,249,.82);
      --needle: #f8fafc;
      --chart-grid-line: rgba(148,163,184,.14);
    }
    :root[data-theme="light"] {
      color-scheme: light;
      --bg: #edf4f8;
      --panel: rgba(255, 255, 255, .82);
      --line: rgba(30, 64, 86, .16);
      --text: #102334;
      --muted: #5e7284;
      --control: rgba(255, 255, 255, .88);
      --card-start: rgba(255, 255, 255, .96);
      --card-end: rgba(240, 247, 250, .94);
      --table-head: #e7f0f5;
      --gauge-track: rgba(51, 78, 96, .14);
      --gauge-tick: rgba(51, 78, 96, .42);
      --gauge-major: rgba(15, 35, 50, .76);
      --needle: #102334;
      --chart-grid-line: rgba(51, 78, 96, .16);
    }
    * { box-sizing: border-box }
    html { min-width: 280px; overflow-x: hidden }
    html.booting body { visibility: hidden }
    [hidden] { display: none !important }
    body {
      margin: 0;
      min-height: 100vh;
      min-height: 100dvh;
      overflow-x: hidden;
      -webkit-text-size-adjust: 100%;
      color: var(--text);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      background:
        radial-gradient(circle at 15% -10%, rgba(14, 165, 233, .2), transparent 34rem),
        radial-gradient(circle at 95% 10%, rgba(52, 211, 153, .12), transparent 28rem),
        var(--bg);
    }
    body::before {
      content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .16;
      background-image: linear-gradient(var(--line) 1px, transparent 1px),
                        linear-gradient(90deg, var(--line) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, black, transparent 75%);
    }
    :root[data-theme="light"] body {
      background:
        radial-gradient(circle at 15% -10%, rgba(14, 165, 233, .15), transparent 34rem),
        radial-gradient(circle at 95% 10%, rgba(52, 211, 153, .1), transparent 28rem),
        var(--bg);
    }
    .shell {
      width: min(1440px, calc(100% - 32px));
      margin: auto;
      padding: max(18px, env(safe-area-inset-top)) 0 max(44px, env(safe-area-inset-bottom));
    }
    header, .panel {
      border: 1px solid var(--line);
      background: var(--panel);
      backdrop-filter: blur(18px);
      box-shadow: 0 18px 55px rgba(0, 0, 0, .28);
    }
    header {
      display: flex; align-items: center; justify-content: space-between; gap: 18px;
      padding: 18px 22px; border-radius: 20px; margin-bottom: 18px;
    }
    .brand { display: flex; align-items: center; gap: 14px; min-width: 0 }
    .brand > div:last-child { min-width: 0 }
    .logo {
      width: 44px; height: 44px; display: grid; place-items: center; border-radius: 14px;
      color: #06131c; font-size: 24px; background: linear-gradient(135deg, var(--amber), #fb923c);
      box-shadow: 0 0 28px rgba(251, 191, 36, .25);
    }
    h1 { margin: 0; font-size: clamp(18px, 2.5vw, 25px); letter-spacing: -.03em }
    .subtitle, .muted { color: var(--muted) }
    .subtitle { overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
    .status { display: flex; align-items: center; gap: 9px; font-weight: 700 }
    .header-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 10px }
    .theme-switch { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 12px; cursor: pointer; user-select: none }
    .theme-switch input { position: absolute; opacity: 0; pointer-events: none }
    .theme-slider {
      position: relative; width: 42px; height: 23px; border-radius: 999px;
      border: 1px solid var(--line); background: var(--control); transition: background .25s ease;
    }
    .theme-slider::after {
      content: "☾"; position: absolute; display: grid; place-items: center;
      width: 19px; height: 19px; left: 1px; top: 1px; border-radius: 50%;
      color: #fff; font-size: 12px; background: #475569; transition: transform .25s ease, background .25s ease;
    }
    .theme-switch input:checked + .theme-slider { background: rgba(251,191,36,.22) }
    .theme-switch input:checked + .theme-slider::after {
      content: "☀"; transform: translateX(19px); color: #412b00; background: var(--amber);
    }
    .theme-switch input:focus-visible + .theme-slider { outline: 3px solid rgba(56,189,248,.25); outline-offset: 2px }
    .language-switch {
      display: flex; align-items: center; gap: 3px; padding: 3px;
      min-height: 40px; border: 1px solid var(--line); border-radius: 12px;
      background: var(--control);
    }
    .language-option {
      min-width: 38px; min-height: 32px; padding: 0 8px; border: 0; border-radius: 9px;
      color: var(--muted); background: transparent; font-size: 11px; font-weight: 800;
    }
    .language-option.active {
      color: #06202a; background: var(--cyan); box-shadow: 0 3px 12px rgba(34,211,238,.22);
    }
    .view-tabs { display: flex; gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: 12px; background: var(--control) }
    .view-tab { min-height: 32px; padding: 0 10px; border: 0; border-radius: 9px; color: var(--muted); background: transparent; font-size: 12px; font-weight: 750 }
    .view-tab.active { color: #06202a; background: var(--cyan); box-shadow: 0 3px 12px rgba(34,211,238,.2) }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--red); box-shadow: 0 0 14px var(--red) }
    .online .dot { background: var(--green); box-shadow: 0 0 14px var(--green) }
    .paused .dot { background: var(--amber); box-shadow: 0 0 14px var(--amber) }
    #app-toggle {
      border-color: rgba(251,113,133,.4);
      background: rgba(127,29,29,.18);
      font-weight: 750;
    }
    #app-toggle.start {
      border-color: rgba(52,211,153,.4);
      background: rgba(16,185,129,.16);
    }
    #register-map-upload-button {
      border-color: rgba(56,189,248,.4);
      background: linear-gradient(135deg, rgba(14,165,233,.18), rgba(34,211,238,.1));
      font-weight: 750;
    }
    .toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 18px }
    .chip, select, button, input {
      min-height: 40px; border: 1px solid var(--line); border-radius: 12px;
      background: var(--control); color: var(--text); padding: 0 13px;
      font: inherit;
    }
    .chip { display: flex; align-items: center }
    select, button { cursor: pointer }
    @media (hover: hover) {
      button:hover, select:hover { border-color: rgba(56, 189, 248, .55) }
    }
    button:focus-visible, select:focus-visible, input:focus-visible {
      outline: 3px solid rgba(56,189,248,.25);
      outline-offset: 2px;
    }
    button:disabled { cursor: wait; opacity: .65 }
    #demo-button {
      border-color: rgba(52, 211, 153, .35);
      background: linear-gradient(135deg, rgba(16,185,129,.18), rgba(14,165,233,.14));
      font-weight: 750;
    }
    #chart-demo-button {
      border-color: rgba(167,139,250,.4);
      background: linear-gradient(135deg, rgba(139,92,246,.2), rgba(14,165,233,.12));
      font-weight: 750;
    }
    .updated { margin-left: auto }
    .energy-flow-card {
      position: sticky; top: 8px; z-index: 8; width: 100%;
      margin-bottom: 18px; padding: 16px 18px 18px;
      overflow: hidden; border: 1px solid rgba(56,189,248,.3); border-radius: 20px;
      background: var(--panel);
      background: linear-gradient(145deg, color-mix(in srgb, var(--card-start) 94%, transparent), color-mix(in srgb, var(--card-end) 94%, transparent));
      box-shadow: 0 18px 46px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.05);
      backdrop-filter: blur(18px);
    }
    .energy-flow-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 13px }
    .energy-flow-head h2 { font-size: 15px }
    .energy-flow-status {
      padding: 5px 10px; border: 1px solid var(--line); border-radius: 999px;
      color: var(--muted); background: var(--control); font-size: 11px; font-weight: 800; text-transform: uppercase;
    }
    .energy-flow-status.active { color: var(--green); border-color: rgba(52,211,153,.4); background: rgba(16,185,129,.13) }
    .energy-flow-scroll { width: 100%; overflow: visible }
    .energy-flow-diagram {
      display: grid;
      grid-template-columns: minmax(130px,1fr) minmax(34px,.32fr) minmax(150px,1.08fr) minmax(34px,.32fr) minmax(130px,1fr);
      grid-template-rows: auto 52px auto; align-items: center; width: 100%; max-width: 1120px; margin: 0 auto;
    }
    .energy-node {
      position: relative; z-index: 2; display: flex; flex-direction: column; justify-content: center;
      width: 100%; min-width: 0; height: 128px; padding: 28px 8px 22px 38px;
      border: 1px solid var(--line); border-radius: 15px; text-align: center;
      background: var(--control); transition: border-color .3s ease, box-shadow .3s ease, transform .3s ease;
    }
    .energy-node.active {
      border-color: var(--node-colour);
      background: color-mix(in srgb, var(--node-colour) 13%, var(--control));
      box-shadow: 0 0 0 2px color-mix(in srgb, var(--node-colour) 28%, transparent), 0 0 24px color-mix(in srgb, var(--node-colour) 32%, transparent);
    }
    .energy-node-icon {
      position: absolute; left: 8px; top: 8px; display: block;
      color: var(--node-colour); font-size: 25px; line-height: 1;
      filter: drop-shadow(0 0 7px currentColor);
    }
    .energy-node-image-icon {
      width: 60px; height: 120px;
      background: var(--node-colour);
      -webkit-mask: var(--node-icon) center / contain no-repeat;
      mask: var(--node-icon) center / contain no-repeat;
    }
    .energy-node-label {
      position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
      overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0;
    }
    .energy-node-register {
      position: absolute; z-index: 1; left: 42px; right: 7px; top: 7px;
      display: -webkit-box; max-width: none; max-height: 21px; overflow: hidden;
      color: var(--node-colour); font-size: 8px; font-weight: 900;
      font-variant-numeric: tabular-nums; letter-spacing: .02em; line-height: 10px;
      text-align: right; white-space: normal; opacity: .88;
      -webkit-box-orient: vertical; -webkit-line-clamp: 2;
    }
    .energy-node-value {
      position: absolute; left: 50%; top: 55%; display: block;
      width: calc(100% - 48px); max-width: none; margin: 0;
      overflow: visible; text-align: center; white-space: normal;
      font-size: 14px; font-weight: 850; font-variant-numeric: tabular-nums;
      transform: translate(-50%,-50%);
    }
    .energy-node-value[hidden] { display: none }
    .energy-solar-values, .energy-inverter-values, .energy-generator-values,
    .energy-home-values, .energy-grid-values, .energy-battery-values {
      display: grid; gap: 2px; margin-top: 0; overflow: visible;
      text-align: center; text-overflow: clip; white-space: normal;
    }
    .energy-solar-values > span, .energy-inverter-values > span,
    .energy-generator-values > span, .energy-home-values > span, .energy-grid-values > span,
    .energy-battery-values > span { white-space: nowrap }
    .energy-inverter-values { gap: 3px }
    .energy-home .energy-node-value { top: 50% }
    .energy-mode-row {
      display: flex; align-items: center; justify-content: center;
      width: 100%; gap: 5px; text-align: center; white-space: normal !important;
    }
    .energy-mode-label {
      color: var(--muted); font-size: 7px; font-weight: 800; letter-spacing: .03em;
      line-height: 1.1; text-align: left; text-transform: uppercase; white-space: normal;
    }
    .energy-mode-value { display: grid; min-width: 0; justify-items: center; line-height: 1.05 }
    .energy-mode-code { color: var(--node-colour); text-align: center; white-space: nowrap }
    .energy-mode-definition {
      max-width: 100%; color: var(--muted); font-size: 6.5px; font-weight: 700;
      line-height: 1.05; text-align: right; white-space: normal;
    }
    .energy-battery-values {
      position: absolute; left: 52%; top: 55%; width: 44%;
      text-align: left; font-size: 14px; transform: translateY(-50%);
    }
    .energy-battery .energy-node-register { left: 52%; right: 4%; text-align: left }
    .energy-battery .flow-direction {
      position: absolute; left: 6px; right: 6px; bottom: 8px; margin: 0; text-align: center;
    }
    .energy-battery-icon {
      --battery-level: 0%;
      left: 4%; top: 23%; bottom: auto; width: 44%; height: 58%;
      overflow: visible; border: 2px solid var(--node-colour); border-radius: 6px;
      background: color-mix(in srgb, var(--node-colour) 8%, var(--control));
      font-size: 8px; filter: drop-shadow(0 0 6px color-mix(in srgb, var(--node-colour) 65%, transparent));
      transform: none;
    }
    .energy-battery-icon::before {
      content: ""; position: absolute; left: 17%; top: -7px; width: 66%; height: 5px;
      border-radius: 2px 2px 0 0;
      background: linear-gradient(to right, var(--node-colour) 0 23%, transparent 23% 77%, var(--node-colour) 77% 100%);
    }
    .energy-battery-icon::after {
      content: ""; position: absolute; left: 28%; right: 28%; top: 7px; height: 12px;
      border: 2px solid color-mix(in srgb, var(--node-colour) 76%, transparent);
      border-bottom: 0; border-radius: 7px 7px 0 0;
    }
    .energy-battery-fill {
      position: absolute; left: 2px; right: 2px; bottom: 2px; width: auto; height: var(--battery-level);
      max-height: calc(100% - 4px); border-radius: 3px;
      background: #22c55e; box-shadow: 0 0 7px rgba(34,197,94,.7);
      transition: height .45s ease;
    }
    .energy-battery-percent {
      position: absolute; z-index: 1; inset: 0; display: grid; place-items: center;
      color: var(--text); font-size: 8px; font-weight: 950; line-height: 1;
      text-shadow: 0 1px 2px var(--card-start), 0 0 3px var(--card-start);
    }
    .energy-solar { grid-column: 1; grid-row: 1; --node-colour: #fbbf24 }
    .energy-inverter { grid-column: 3; grid-row: 1; --node-colour: #22d3ee }
    .energy-home {
      grid-column: 5; grid-row: 1; --node-colour: #a78bfa;
      --node-icon: url('/assets/home.svg');
    }
    .energy-solar .energy-node-icon,
    .energy-inverter .energy-node-icon,
    .energy-home .energy-node-icon {
      left: 7px; top: 7px; bottom: 7px; display: grid; place-items: center;
      width: 60px; height: auto; font-size: 52px;
    }
    .energy-inverter {
      height: 148px; padding-inline: 8px;
      --node-icon: url('/assets/inverter.svg');
    }
    .energy-inverter .energy-node-icon {
      inset: 0; z-index: 0; width: 100%; height: 100%; opacity: .13;
      font-size: 76px; filter: none;
    }
    .energy-home .energy-node-icon {
      inset: 0; z-index: 0; width: 100%; height: 100%; opacity: .18;
      filter: none;
    }
    .energy-inverter .energy-node-register {
      left: 7px; right: 7px; text-align: center;
    }
    .energy-inverter .energy-node-value {
      z-index: 1; left: 50%; width: calc(100% - 16px); font-size: 12px;
      text-shadow: 0 1px 3px var(--card-start), 0 0 5px var(--card-start);
    }
    .energy-inverter-load {
      position: absolute; z-index: 2; left: 50%; top: 28px;
      color: var(--node-colour); font-size: 22px; font-weight: 950; line-height: 1;
      text-align: center; white-space: nowrap; transform: translateX(-50%);
    }
    .energy-inverter-load-definition {
      margin-top: -2px; color: var(--muted); font-size: 6.5px; font-weight: 700;
      line-height: 1.05; white-space: normal !important;
    }
    .energy-inverter-load-definition,
    .energy-inverter-fan-row > span[data-i18n],
    .energy-inverter .energy-mode-label,
    .energy-inverter .energy-mode-definition { display: none }
    .energy-inverter-fan-row {
      display: flex; align-items: center; justify-content: center; gap: 4px;
      color: var(--muted); font-size: 7px; font-weight: 800; line-height: 1;
    }
    .energy-inverter-fan-icon {
      display: block; flex: 0 0 30px; width: 30px; height: 30px; max-height: none; margin: 0;
      overflow: visible; color: var(--node-colour); line-height: 1;
      filter: drop-shadow(0 0 4px color-mix(in srgb, var(--node-colour) 65%, transparent));
      transform-origin: center;
    }
    .energy-inverter-fan-row.active .energy-inverter-fan-icon { animation: inverter-fan-spin 1s linear infinite }
    .energy-inverter-fan-value { color: var(--text); font-size: 14px; font-weight: 950; font-variant-numeric: tabular-nums }
    .energy-inverter .energy-mode-code { font-size: 14px; font-weight: 950 }
    @keyframes inverter-fan-spin { to { transform: rotate(360deg) } }
    .energy-battery { grid-column: 1; grid-row: 3; padding-inline: 0; --node-colour: #34d399 }
    .energy-grid {
      grid-column: 3; grid-row: 3; padding-left: 68px; --node-colour: #60a5fa;
      --node-icon: url('/assets/grid.png');
    }
    .energy-grid .energy-node-image-icon {
      left: 7px; top: 7px; bottom: 7px; width: 60px; height: auto;
    }
    .energy-generator {
      grid-column: 5; grid-row: 3; padding-left: 48px; --node-colour: #fb923c;
      --node-icon: url('/assets/generator.png');
    }
    .energy-generator .energy-node-image-icon {
      left: 7px; top: 7px; bottom: 7px; width: 60px; height: auto;
    }
    .flow-connector {
      position: relative; align-self: stretch; justify-self: stretch;
      min-width: 0; min-height: 0; overflow: hidden; color: var(--muted); opacity: .38;
    }
    .flow-lines { position: absolute; inset: 0; display: block; width: 100%; height: 100%; overflow: hidden }
    .flow-line {
      fill: none; stroke: currentColor; stroke-width: 3; stroke-linecap: butt;
      stroke-dasharray: 11 6; vector-effect: non-scaling-stroke;
      animation: none;
    }
    .flow-line-mobile { display: none }
    .flow-connector.active { z-index: 4; color: var(--flow-colour,#22d3ee); opacity: 1 }
    .flow-connector.disconnected { opacity: 0 }
    .flow-connector.disconnected .flow-line { animation: none }
    .flow-connector.active .flow-line {
      stroke-width: 6; filter: drop-shadow(0 0 5px currentColor);
      animation: energy-track var(--flow-duration,1.4s) linear infinite;
    }
    .flow-connector.reverse .flow-line { animation-direction: reverse }
    .flow-pv { grid-column: 2; grid-row: 1; --flow-colour: #fbbf24 }
    .flow-home { grid-column: 4; grid-row: 1; --flow-colour: #a78bfa }
    .flow-battery { grid-column: 2; grid-row: 2; --flow-colour: #34d399 }
    .flow-grid { grid-column: 3; grid-row: 2; --flow-colour: #60a5fa }
    .flow-generator { grid-column: 4; grid-row: 2; --flow-colour: #fb923c }
    .flow-direction {
      position: absolute; left: 6px; right: 6px; bottom: 8px; display: block;
      min-height: 10px; margin: 0; overflow: hidden; color: var(--node-colour);
      text-align: center; text-overflow: ellipsis; font-size: 8px; font-weight: 900;
      line-height: 10px; white-space: nowrap;
    }
    @keyframes energy-track { to { stroke-dashoffset: -34 } }
    .solar-energy-panel { margin-bottom: 18px }
    .solar-energy-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px }
    .solar-energy-note { color: var(--muted); font-size: 10px; text-align: right }
    .solar-energy-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 10px }
    .solar-energy-total {
      min-width: 0; padding: 12px; border: 1px solid rgba(251,191,36,.22); border-radius: 14px;
      background: linear-gradient(145deg, rgba(251,191,36,.09), rgba(14,165,233,.05));
    }
    .solar-energy-period { display: block; color: var(--muted); font-size: 10px; font-weight: 800; text-transform: uppercase }
    .solar-energy-value { display: block; margin-top: 4px; color: #fbbf24; font-size: clamp(19px,2.2vw,27px); font-weight: 900; font-variant-numeric: tabular-nums }
    .solar-energy-error { margin-top: 9px; color: var(--red); font-size: 11px }
    .gauges {
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px;
      margin-bottom: 18px;
    }
    .gauge-card {
      position: relative; min-width: 0; overflow: hidden; padding: 16px 16px 14px;
      border: 1px solid var(--line); border-radius: 18px;
      background: linear-gradient(145deg, var(--card-start), var(--card-end));
      box-shadow: inset 0 1px rgba(255,255,255,.035), 0 14px 34px rgba(0,0,0,.2);
    }
    .gauge-card[draggable="true"] { cursor: grab }
    .gauge-card[draggable="true"]:active { cursor: grabbing }
    .gauge-card.dragging { opacity: .38; transform: scale(.98) }
    .gauge-card.drag-target { border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(34,211,238,.14) }
    .gauge-card::after {
      content: ""; position: absolute; width: 120px; height: 120px; right: -55px; top: -60px;
      border-radius: 50%; background: var(--accent); opacity: .08; filter: blur(12px);
    }
    .gauge-heading { display: flex; align-items: center; gap: 7px; min-width: 0; padding-right: 62px }
    .gauge-title { min-width: 0; overflow: hidden; font-weight: 700; text-overflow: ellipsis; white-space: nowrap }
    .gauge-number {
      flex: none; padding: 2px 6px; border: 1px solid color-mix(in srgb, var(--accent) 52%, var(--line));
      border-radius: 999px; color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, var(--control));
      font-size: 9px; font-weight: 900; font-variant-numeric: tabular-nums; line-height: 1.35;
    }
    .gauge-actions { position: absolute; z-index: 2; right: 8px; top: 7px; display: flex; align-items: center; gap: 1px }
    .drag-handle, .gauge-actions .remove-value {
      position: static; width: 27px; min-height: 27px; padding: 0; border: 0;
      background: transparent; color: var(--muted); font-size: 18px; line-height: 1;
    }
    .drag-handle { cursor: grab; font-size: 17px; touch-action: none; user-select: none; -webkit-user-select: none }
    .drag-handle:active { cursor: grabbing }
    .gauge-card.pointer-dragging { opacity: .55; transform: scale(.98); z-index: 3 }
    .gauge-card.no-speedometer {
      display: flex; min-height: 245px; flex-direction: column;
    }
    .gauge-card.no-speedometer .reading {
      flex: 1; margin: 0; justify-content: center; align-items: center;
    }
    .gauge-card.no-speedometer .source { margin-top: auto }
    .gauges.empty-dashboard { grid-template-columns: minmax(220px, 330px); justify-content: center }
    .add-gauge-card {
      display: grid; place-items: center; align-content: center; gap: 8px; min-height: 245px;
      padding: 24px; border: 1px dashed rgba(56,189,248,.42); border-radius: 18px;
      background: linear-gradient(145deg, rgba(56,189,248,.08), rgba(34,211,238,.035));
      color: var(--muted); text-align: center; cursor: pointer;
    }
    .add-gauge-card:hover { border-color: var(--cyan); color: var(--text); background: rgba(56,189,248,.12) }
    .add-gauge-plus { color: var(--cyan); font-size: 54px; font-weight: 300; line-height: .9 }
    .add-gauge-label { font-size: 13px; font-weight: 700 }
    .dashboard-gauge-toolbar { display: flex; justify-content: flex-end; margin: -4px 0 10px }
    .dashboard-gauge-toolbar[hidden] { display: none }
    .dashboard-gauge-toolbar button { min-height: 36px; padding: 8px 12px }
    .clear-selection { border-color: rgba(248,113,113,.36); color: var(--red) }
    dialog.gauge-picker {
      width: min(620px, calc(100vw - 24px)); max-height: min(760px, calc(100vh - 24px));
      padding: 0; overflow: hidden; color: var(--text); border: 1px solid var(--line);
      border-radius: 20px; background: var(--panel); box-shadow: 0 28px 90px rgba(0,0,0,.55);
    }
    dialog.gauge-picker::backdrop { background: rgba(2,6,23,.72); backdrop-filter: blur(5px) }
    .gauge-picker-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 15px; padding: 18px 18px 12px }
    .gauge-picker-head h2 { margin-bottom: 5px }
    .gauge-picker-close { width: 36px; min-height: 36px; padding: 0; font-size: 22px }
    .gauge-picker-search { width: calc(100% - 36px); margin: 0 18px 12px }
    .gauge-picker-actions { display: flex; justify-content: flex-end; gap: 8px; padding: 0 18px 12px }
    .gauge-picker-actions button { min-height: 34px; padding: 7px 12px }
    .gauge-picker-list { max-height: min(590px, calc(100vh - 190px)); overflow-y: auto; padding: 0 18px 18px }
    .gauge-picker-option { display: flex; align-items: center; gap: 11px; padding: 11px 5px; border-bottom: 1px solid var(--line); cursor: pointer }
    .gauge-picker-option:hover { background: rgba(56,189,248,.05) }
    .gauge-picker-option input { flex: 0 0 auto; width: 18px; min-height: 18px; margin: 0; accent-color: var(--cyan) }
    .gauge-picker-name { min-width: 0; font-weight: 700 }
    .gauge-picker-name small { display: block; margin-top: 3px; color: var(--muted); font-weight: 400 }
    svg { display: block; width: 100%; max-height: 150px; margin-top: 3px; overflow: visible }
    .track { fill: none; stroke: var(--gauge-track); stroke-width: 13; stroke-linecap: round }
    .progress {
      fill: none; stroke: var(--accent); stroke-width: 13; stroke-linecap: round;
      stroke-dasharray: 283; stroke-dashoffset: 283;
      transition: stroke-dashoffset .7s ease;
    }
    .needle {
      stroke: var(--needle); stroke-width: 3.5; stroke-linecap: round;
      transform-origin: 120px 120px; transform: rotate(-90deg);
      transition: transform .75s cubic-bezier(.2,.8,.2,1);
    }
    .hub { fill: var(--accent); stroke: #e2e8f0; stroke-width: 2 }
    .tick { stroke: var(--gauge-tick); stroke-width: 1.2 }
    .tick.major { stroke: var(--gauge-major); stroke-width: 2 }
    .scale-label {
      fill: var(--muted); font-size: 8px; font-weight: 700;
      text-anchor: middle; dominant-baseline: middle;
    }
    .reading { display: flex; justify-content: center; align-items: baseline; gap: 7px; margin-top: -13px }
    .value { font-size: 27px; font-weight: 800; letter-spacing: -.04em; font-variant-numeric: tabular-nums }
    .unit { color: var(--muted); font-weight: 700 }
    .source { margin-top: 5px; color: var(--muted); text-align: center; font-size: 11px }
    .panel { padding: 18px; border-radius: 18px }
    .panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px }
    .register-logger { margin-bottom: 18px }
    .logger-layout { display: flex; align-items: center; justify-content: space-between; gap: 18px }
    .logger-copy { min-width: 0 }
    .logger-status { margin-top: 7px; color: var(--muted); overflow-wrap: anywhere }
    .logger-status.active { color: var(--green) }
    .logger-status.error-text { color: var(--red) }
    .logger-actions { display: flex; flex: 0 0 auto; flex-wrap: wrap; gap: 8px }
    .logger-note { width: min(300px, 100%); flex: 1 1 220px }
    .logger-actions button, .logger-download {
      display: inline-flex; align-items: center; justify-content: center; min-height: 40px;
      padding: 0 13px; border: 1px solid var(--line); border-radius: 12px;
      color: var(--text); background: var(--control); text-decoration: none; font: inherit;
    }
    #register-log-start { border-color: rgba(52,211,153,.4); background: rgba(16,185,129,.16) }
    #register-log-stop { border-color: rgba(251,113,133,.4); background: rgba(127,29,29,.18) }
    h2 { margin: 0; font-size: 16px }
    input { width: min(270px, 46vw); outline: none }
    input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(56,189,248,.12) }
    .table-wrap { overflow: auto; max-height: 430px; border-radius: 12px }
    table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums }
    th { position: sticky; top: 0; z-index: 1; background: var(--table-head); color: var(--muted); text-align: left; font-size: 11px; letter-spacing: .08em; text-transform: uppercase }
    th, td { padding: 10px 12px; border-bottom: 1px solid var(--line) }
    tbody tr:hover { background: rgba(56,189,248,.05) }
    tbody tr.unavailable { opacity: .48 }
    td:nth-child(1), td:nth-child(4), td:nth-child(5) { white-space: nowrap }
    .error { display: none; margin-bottom: 15px; color: #fecdd3; border-color: rgba(251,113,133,.35); background: rgba(127,29,29,.24) }
    .error.show { display: block }
    .lcd-panel { max-width: 1080px; margin: 0 auto }
    .lcd-screen {
      overflow: hidden; padding: clamp(16px, 3vw, 32px); border: 8px solid #263238;
      border-radius: 22px; color: #10241d; background: linear-gradient(145deg, #c9e3c4, #a9caa7);
      box-shadow: inset 0 0 35px rgba(24,54,40,.2), 0 22px 65px rgba(0,0,0,.35);
      font-family: "Courier New", ui-monospace, monospace; font-variant-numeric: tabular-nums;
    }
    .lcd-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding-bottom: 14px; border-bottom: 2px solid rgba(16,36,29,.25) }
    .lcd-head h2 { font: 900 clamp(18px,3vw,28px)/1.1 inherit; letter-spacing: .08em }
    .lcd-subtitle { margin-top: 4px; opacity: .68; font-size: 12px }
    .lcd-mode { padding: 5px 10px; border: 2px solid currentColor; border-radius: 6px; font-weight: 900; text-transform: uppercase }
    .lcd-flow { display: grid; grid-template-columns: minmax(0,1fr) auto minmax(0,1fr) auto minmax(0,1fr); align-items: center; gap: 9px; margin: 24px 0 }
    .lcd-node { min-width: 0; padding: 12px 8px; border: 2px solid rgba(16,36,29,.34); border-radius: 9px; text-align: center; opacity: .52 }
    .lcd-node.active { opacity: 1; border-color: currentColor; box-shadow: inset 0 0 0 2px rgba(16,36,29,.1) }
    .lcd-node-icon { display: block; font: 900 25px/1 system-ui; margin-bottom: 5px }
    .lcd-node-label { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; font-weight: 900; text-transform: uppercase }
    .lcd-node-value { display: block; margin-top: 3px; font-size: clamp(14px,2vw,20px); font-weight: 900 }
    .lcd-arrow { text-align: center; font-size: 25px; font-weight: 900; opacity: .35 }
    .lcd-arrow.active { opacity: 1; animation: lcd-pulse 1.2s ease-in-out infinite }
    .lcd-main { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; margin-bottom: 14px }
    .lcd-primary { padding: 15px; border: 2px solid rgba(16,36,29,.3); border-radius: 9px; text-align: center }
    .lcd-primary.active { border-color: currentColor; box-shadow: inset 0 0 0 2px rgba(16,36,29,.1) }
    .lcd-primary-label, .lcd-readout-label { display: block; font-size: 10px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; opacity: .7 }
    .lcd-primary-value { display: block; margin-top: 4px; font-size: clamp(26px,5vw,46px); font-weight: 900; letter-spacing: -.06em }
    .lcd-readouts { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 8px }
    .lcd-readout { min-width: 0; padding: 11px; border-top: 2px solid rgba(16,36,29,.28) }
    .lcd-readout-value { display: block; margin-top: 3px; overflow-wrap: anywhere; font-size: clamp(14px,2vw,20px); font-weight: 900 }
    .lcd-status-line { margin-top: 16px; padding-top: 13px; border-top: 2px solid rgba(16,36,29,.25); font-weight: 900 }
    .lcd-page-panel { margin-top: 17px; padding: 14px; border: 2px solid rgba(16,36,29,.35); border-radius: 9px; background: rgba(220,239,211,.22) }
    .lcd-page-head { display: flex; align-items: center; justify-content: space-between; gap: 12px }
    .lcd-page-code { padding: 2px 7px; border: 2px solid currentColor; border-radius: 5px; font-size: 18px; font-weight: 900 }
    .lcd-page-title { text-align: right; font-weight: 900; text-transform: uppercase }
    .lcd-page-values { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 9px; margin-top: 12px }
    .lcd-page-reading { padding-top: 9px; border-top: 2px solid rgba(16,36,29,.24) }
    .lcd-page-description { margin-top: 10px; min-height: 2.8em; font: 600 12px/1.4 system-ui,sans-serif; opacity: .75 }
    .lcd-controls-wrap { margin-top: 16px; padding-top: 16px; border-top: 2px solid rgba(16,36,29,.25) }
    .lcd-controls-title { font: 900 11px/1.2 system-ui,sans-serif; letter-spacing: .08em; text-transform: uppercase; opacity: .7 }
    .lcd-controls { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 9px; margin-top: 9px }
    .lcd-key { min-height: 48px; border: 3px solid #17231f; border-radius: 9px; color: #d4e8d0; background: #263731; box-shadow: inset 0 -4px rgba(0,0,0,.24), 0 3px 0 #101915; font: 900 13px/1 system-ui,sans-serif }
    .lcd-key:active { transform: translateY(2px); box-shadow: inset 0 -2px rgba(0,0,0,.2), 0 1px 0 #101915 }
    .lcd-controls-note { margin-top: 10px; font: 600 11px/1.4 system-ui,sans-serif; opacity: .68 }
    @keyframes lcd-pulse { 50% { transform: translateX(3px); opacity: .55 } }
    .charts-layout {
      display: grid; grid-template-columns: 290px minmax(0, 1fr); gap: 16px;
      align-items: start;
    }
    .chart-selector { position: sticky; top: 14px; max-height: calc(100vh - 28px) }
    .chart-selector input[type="search"] { width: 100%; margin: 14px 0 10px }
    .chart-selector-actions { display: flex; gap: 8px; margin-bottom: 10px }
    .chart-selector-actions button { flex: 1 1 0; min-height: 34px; padding: 7px 9px }
    .value-list { overflow-y: auto; max-height: calc(100vh - 229px); padding-right: 4px }
    .value-option {
      padding: 9px 5px; border-bottom: 1px solid var(--line);
    }
    .value-option:hover { background: rgba(56,189,248,.05) }
    .value-name { min-width: 0; font-weight: 650 }
    .value-name small { display: block; color: var(--muted); margin-top: 2px; font-weight: 400 }
    .value-targets { display: flex; gap: 12px; margin-top: 7px }
    .value-targets label { display: flex; align-items: center; gap: 5px; color: var(--muted); font-size: 11px; cursor: pointer }
    .value-targets input { width: 14px; min-height: 14px; margin: 0; accent-color: var(--cyan) }
    .custom-values { margin-bottom: 18px }
    .custom-value-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 12px }
    .custom-value-card {
      position: relative; min-width: 0; padding: 15px; border: 1px solid var(--line);
      border-radius: 16px; background: linear-gradient(145deg, var(--card-start), var(--card-end));
    }
    .custom-value-label { color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 24px }
    .custom-value-reading { margin-top: 7px; font-size: 25px; font-weight: 800; font-variant-numeric: tabular-nums }
    .custom-value-detail { color: var(--muted); font-size: 11px; margin-top: 4px }
    .remove-value {
      position: absolute; right: 8px; top: 7px; width: 27px; min-height: 27px; padding: 0;
      border: 0; background: transparent; color: var(--muted); font-size: 18px;
    }
    .charts-main { min-width: 0 }
    .charts-head { margin-bottom: 14px }
    .chart-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px }
    .chart-card {
      min-width: 0; padding: 16px; border: 1px solid var(--line); border-radius: 18px;
      background: linear-gradient(145deg, var(--card-start), var(--card-end));
    }
    .chart-card-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px }
    .chart-card h3 { margin: 0; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
    .chart-latest { color: var(--accent); font-size: 20px; font-weight: 800; white-space: nowrap }
    .chart-card canvas { display: block; width: 100%; max-width: 100%; height: 220px; margin-top: 8px }
    .chart-empty {
      display: grid; place-items: center; min-height: 340px; color: var(--muted);
      border: 1px dashed rgba(148,163,184,.22); border-radius: 18px; text-align: center; padding: 24px;
    }
    @media (min-width: 641px) {
      .energy-solar,
      .energy-grid,
      .energy-generator { padding-inline: 8px }
      .energy-solar .energy-node-icon,
      .energy-grid .energy-node-image-icon,
      .energy-generator .energy-node-image-icon {
        inset: 0; z-index: 0; display: grid; place-items: center;
        width: 100%; height: 100%; opacity: .18; filter: none;
        -webkit-mask-position: center;
        mask-position: center;
        -webkit-mask-size: 100% 100%;
        mask-size: 100% 100%;
      }
      .energy-solar .energy-node-icon { font-size: 112px }
      .energy-solar .energy-node-register,
      .energy-grid .energy-node-register,
      .energy-generator .energy-node-register {
        left: 8px; right: 8px; text-align: center;
      }
      .energy-solar .energy-node-value,
      .energy-grid .energy-node-value,
      .energy-generator .energy-node-value {
        z-index: 1; left: 50%; width: calc(100% - 16px);
        font-size: 16px; text-align: center;
        text-shadow: 0 1px 3px var(--card-start), 0 0 5px var(--card-start);
        transform: translate(-50%,-50%);
      }
      .energy-solar .flow-direction,
      .energy-grid .flow-direction,
      .energy-generator .flow-direction {
        z-index: 1; left: 8px; right: 8px; text-align: center;
        text-shadow: 0 1px 3px var(--card-start), 0 0 5px var(--card-start);
      }
    }
    @media (max-width: 1120px) {
      .gauges, .custom-value-grid { grid-template-columns: repeat(3, minmax(0, 1fr)) }
      .charts-layout { grid-template-columns: 250px minmax(0, 1fr) }
      .chart-grid { grid-template-columns: 1fr }
    }
    @media (max-width: 900px) {
      .shell { width: min(100% - 24px, 1440px); padding-top: max(12px, env(safe-area-inset-top)) }
      header { align-items: flex-start; flex-direction: column; padding: 16px 18px }
      .brand, .header-actions { width: 100% }
      .header-actions { justify-content: flex-start }
      .status { margin-left: auto }
      .gauges, .custom-value-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) }
      .logger-layout { align-items: stretch; flex-direction: column }
      .logger-actions > * { flex: 1 1 140px }
      .charts-layout { grid-template-columns: 1fr }
      .chart-selector { position: static; max-height: none }
      .value-list { max-height: min(42vh, 360px) }
    }
    @media (max-width: 640px) {
      .shell { width: min(100% - 16px, 1440px); padding-top: max(8px, env(safe-area-inset-top)) }
      .shell:has(#dashboard-view:not([hidden])) {
        display: flex; flex-direction: column;
      }
      .shell:has(#dashboard-view:not([hidden])) > header { order: 2 }
      #dashboard-view:not([hidden]) { display: contents }
      #dashboard-view > * { order: 4 }
      #dashboard-view > .error { order: 0 }
      #dashboard-view > .energy-flow-card { order: 1 }
      #dashboard-view > .toolbar { order: 3 }
      header { gap: 14px; padding: 14px; border-radius: 16px; margin-bottom: 12px }
      .logo { width: 40px; height: 40px; flex: 0 0 40px; border-radius: 12px; font-size: 21px }
      .header-actions {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        align-items: center;
        gap: 8px;
      }
      .header-actions button { width: 100%; min-width: 0; padding-inline: 8px }
      .view-tabs { grid-column: 1 / -1; width: 100% }
      .view-tab { flex: 1 1 0 }
      .theme-switch { min-height: 44px }
      .status { justify-self: end; margin-left: 0; min-height: 44px }
      .toolbar {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
        margin-bottom: 12px;
      }
      .toolbar > * { width: 100%; min-width: 0; margin: 0 }
      .toolbar .chip { justify-content: space-between; padding-inline: 10px }
      .toolbar select { width: auto; min-width: 0; min-height: 36px; padding-inline: 7px }
      #demo-button, #manage-values-button, #updated { grid-column: 1 / -1 }
      .updated { margin-left: 0 }
      .gauges { gap: 8px; margin-bottom: 12px }
      .energy-flow-card {
        position: relative; top: auto; width: 100%; max-width: 100%;
        margin-bottom: 12px; padding: 12px 8px 14px; border-radius: 16px;
      }
      .energy-flow-head { min-width: 0; margin-bottom: 11px; padding-inline: 3px }
      .energy-flow-head h2 { flex: 0 1 auto; min-width: 0; font-size: 14px }
      .energy-flow-status {
        flex: 0 1 auto; max-width: 66%; padding: 5px 9px; overflow: hidden;
        font-size: 9px; text-overflow: ellipsis; white-space: nowrap;
      }
      .energy-flow-diagram {
        grid-template-columns: minmax(0,1fr) clamp(24px,8vw,36px) minmax(0,1.08fr) clamp(24px,8vw,36px) minmax(0,1fr);
        grid-template-rows: 136px 46px 136px;
      }
      .solar-energy-grid { grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px }
      .solar-energy-head { align-items: flex-start; flex-direction: column; gap: 4px }
      .solar-energy-note { text-align: left }
      .energy-node { height: 136px; padding: 29px 4px 22px; border-radius: 12px }
      .energy-node-icon { left: 6px; top: 7px; font-size: 21px }
      .energy-node-register {
        left: 5px; top: 7px; right: 5px; max-width: none;
        max-height: 25px; overflow: hidden; font-size: 6.5px; line-height: 8px;
        text-align: center; white-space: normal;
        -webkit-box-orient: vertical; -webkit-line-clamp: 2;
      }
      .energy-node-value {
        left: 50%; top: 55%; width: calc(100% - 8px); max-width: none;
        overflow: visible; font-size: 11.5px;
      }
      .energy-inverter-values, .energy-home-values { font-size: 10.5px; line-height: 1.12 }
      .energy-inverter .energy-node-value { width: calc(100% - 6px); font-size: 10.5px }
      .energy-inverter-load { font-size: 21px }
      .energy-inverter-fan-row { gap: 3px; font-size: 6px }
      .energy-inverter-fan-icon { flex-basis: 32px; width: 32px; height: 32px }
      .energy-inverter-fan-value { font-size: 15px }
      .energy-mode-row { gap: 3px }
      .energy-mode-label { font-size: 6.5px; letter-spacing: 0 }
      .energy-solar-values { gap: 3px; line-height: 1.12 }
      .energy-battery { padding-left: 39px }
      .energy-generator { padding-left: 43px }
      .energy-generator .energy-node-image-icon { left: 5px; top: 7px; bottom: 7px; height: auto }
      .energy-battery-icon {
        font-size: 7px;
      }
      .energy-battery-percent { padding-inline: 1px; overflow: hidden; font-size: 24px }
      .energy-battery-values {
        max-width: none; gap: 3px;
        overflow: visible; font-size: 11.5px; line-height: 1.1;
      }
      .energy-battery .flow-direction { left: 3px; right: 3px; bottom: 7px; text-align: center }
      .energy-node:not(.energy-battery) .flow-direction { bottom: 7px }
      .flow-direction { left: 3px; right: 3px; font-size: 7px }
      .gauge-card { padding: 11px 8px 10px; border-radius: 15px }
      .gauge-heading { gap: 5px; padding-right: 56px }
      .gauge-title { font-size: 12px }
      .gauge-number { padding-inline: 5px; font-size: 8px }
      .value { font-size: clamp(21px, 7vw, 26px) }
      .source { overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
      .panel { padding: 14px; border-radius: 16px }
      .panel-head { align-items: stretch; flex-direction: column }
      .panel-head input { width: 100% }
      .custom-values { margin-bottom: 12px }
      .custom-value-grid { gap: 8px }
      .custom-value-card { padding: 12px; border-radius: 14px }
      .custom-value-reading { font-size: 21px }
      .charts-head #chart-demo-button { width: 100% }
      .chart-grid { gap: 10px }
      .chart-card { padding: 12px 10px; border-radius: 15px }
      .chart-card-head { align-items: flex-start }
      .chart-latest { font-size: 17px }
      .chart-card canvas { height: 190px }
      .chart-empty { min-height: 220px }
      .lcd-screen { border-width: 5px; border-radius: 16px }
      .lcd-flow { gap: 5px }
      .lcd-node { padding: 9px 4px }
      .lcd-node-icon { font-size: 20px }
      .lcd-arrow { font-size: 18px }
      .lcd-main { grid-template-columns: 1fr }
      .lcd-readouts { grid-template-columns: repeat(2,minmax(0,1fr)) }
      .lcd-controls { grid-template-columns: repeat(2,minmax(0,1fr)) }
      .table-wrap { max-height: none; overflow: visible }
      table, tbody { display: block; width: 100% }
      thead { display: none }
      tbody { display: grid; gap: 8px }
      tbody tr {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: center;
        gap: 4px 12px;
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--control);
      }
      tbody td { display: block; min-width: 0; padding: 0; border: 0 }
      tbody td:nth-child(1) { grid-column: 1; grid-row: 1; color: var(--muted); font-size: 11px }
      tbody td:nth-child(2), tbody td:nth-child(5) { display: none }
      tbody td:nth-child(3) {
        grid-column: 1 / -1; grid-row: 2;
        overflow-wrap: anywhere;
      }
      tbody td:nth-child(4) {
        grid-column: 2; grid-row: 1;
        justify-self: end; text-align: right; font-weight: 750;
      }
      input, select, button, .chip { min-height: 44px }
    }
    @media (max-width: 390px) {
      .header-actions { grid-template-columns: 1fr }
      .theme-switch, .status { justify-self: stretch }
      .status { justify-content: flex-start }
      .toolbar { grid-template-columns: 1fr }
      .toolbar > *, #demo-button, #manage-values-button, #cycle, #updated { grid-column: 1 }
      .gauges, .custom-value-grid { grid-template-columns: 1fr }
      .gauge-card svg { max-height: 135px }
      .energy-flow-card { padding-inline: 6px }
      .energy-flow-head h2 { font-size: 13px }
      .energy-flow-status { max-width: 62%; padding-inline: 7px; font-size: 8px }
      .energy-flow-diagram {
        grid-template-columns: minmax(0,1fr) 22px minmax(0,1.06fr) 22px minmax(0,1fr);
        grid-template-rows: 140px 42px 140px;
      }
      .energy-node { height: 140px; padding: 29px 3px 22px }
      .energy-node-icon { left: 5px; font-size: 19px }
      .energy-node-register { left: 3px; right: 3px; max-width: none; font-size: 6px }
      .energy-node-value { width: calc(100% - 6px); font-size: 10.5px }
      .energy-inverter-values, .energy-home-values { font-size: 9.5px }
      .energy-mode-label { font-size: 5.8px }
      .energy-battery { padding-inline: 0 }
      .energy-generator { padding-left: 38px }
      .energy-generator .energy-node-image-icon { left: 4px; top: 6px; bottom: 6px;  height: auto }
      .energy-battery-values { font-size: 10.5px }
      .energy-battery .flow-direction { left: 3px; right: 3px }
      .chart-card-head { flex-direction: column; gap: 3px }
    }
    @media (max-width: 640px) {
      .energy-solar .energy-node-icon,
      .energy-inverter .energy-node-icon,
      .energy-home .energy-node-icon,
      .energy-grid .energy-node-image-icon,
      .energy-generator .energy-node-image-icon {
        inset: 0; z-index: 0; width: 100%; height: 100%; opacity: .18;
        filter: none;
        -webkit-mask-position: center;
        mask-position: center;
        -webkit-mask-size: 100% 100%;
        mask-size: 100% 100%;
      }
      .energy-solar .energy-node-icon,
      .energy-inverter .energy-node-icon,
      .energy-home .energy-node-icon { font-size: clamp(64px, 20vw, 86px) }
      .energy-home .energy-node-icon { font-size: clamp(112px, 34vw, 138px) }
      .energy-solar .energy-node-register,
      .energy-solar .energy-node-value,
      .energy-solar .flow-direction,
      .energy-inverter .energy-node-register,
      .energy-inverter .energy-node-value,
      .energy-inverter .flow-direction,
      .energy-home .energy-node-register,
      .energy-home .energy-node-value,
      .energy-home .flow-direction,
      .energy-grid .energy-node-register,
      .energy-grid .energy-node-value,
      .energy-grid .flow-direction,
      .energy-generator .energy-node-register,
      .energy-generator .energy-node-value,
      .energy-generator .flow-direction {
        z-index: 1;
        text-shadow: 0 1px 3px var(--card-start), 0 0 5px var(--card-start);
      }
      .energy-flow-scroll {
        margin-inline: 0; padding: 2px; overflow: visible;
        overscroll-behavior: auto; scrollbar-width: none; touch-action: pan-y;
      }
      .energy-flow-scroll:focus-visible {
        outline: 2px solid rgba(56,189,248,.45); outline-offset: 2px; border-radius: 10px;
      }
      .energy-flow-scroll::-webkit-scrollbar { display: none }
      .energy-flow-diagram {
        --mobile-inverter-height: clamp(180px, 52vw, 204px);
        width: 100%; min-width: 0; max-width: none;
        grid-template-columns: minmax(0,1fr) 18px minmax(0,1fr);
        grid-template-rows: 126px 24px var(--mobile-inverter-height) 24px 126px;
      }
      .energy-solar { grid-column: 1; grid-row: 1 }
      .energy-home { grid-column: 3; grid-row: 1 }
      .energy-inverter { grid-column: 1; grid-row: 3 }
      .energy-battery { grid-column: 3; grid-row: 3 }
      .energy-grid { grid-column: 1; grid-row: 5 }
      .energy-generator { grid-column: 3; grid-row: 5 }
      .flow-pv { grid-column: 1; grid-row: 2 }
      .flow-home { grid-column: 2; grid-row: 2 }
      .flow-battery { grid-column: 2; grid-row: 3 }
      .flow-grid { grid-column: 1; grid-row: 4 }
      .flow-generator { grid-column: 2; grid-row: 4 }
      .flow-line-desktop { display: none }
      .flow-line-mobile { display: block }
      .energy-node {
        height: 126px; padding: 27px 2px 21px; border-radius: 12px;
      }
      .energy-inverter { height: var(--mobile-inverter-height); overflow: hidden }
      .energy-node-register {
        left: 6px; right: 6px; top: 7px; max-height: 20px;
        font-size: 7px; line-height: 9px;
      }
      .energy-node-value,
      .energy-inverter .energy-node-value {
        left: 50%; top: 54%; width: calc(100% - 12px);
        font-size: 11px; line-height: 1.12;
      }
      .energy-inverter .energy-node-value { top: 52% }
      .energy-home .energy-node-value { top: 49% }
      .energy-inverter-values { min-width: 0; overflow: hidden; font-size: 10px; line-height: 1.1 }
      .energy-home-values { font-size: 11px; line-height: 1.12 }
      .energy-inverter-load { top: 30px; font-size: 24px }
      .energy-inverter-load-definition { max-width: 100%; overflow-wrap: anywhere; font-size: 6px }
      .energy-inverter-fan-row {
        max-width: 100%; flex-wrap: wrap; gap: 2px 3px; overflow-wrap: anywhere;
        font-size: 5.8px; line-height: 1.08; white-space: normal !important;
      }
      .energy-inverter-fan-icon { flex-basis: 38px; width: 38px; height: 38px }
      .energy-inverter-fan-value { font-size: 18px }
      .energy-mode-row {
        display: flex; align-items: center; justify-content: center; gap: 3px; text-align: center;
      }
      .energy-mode-label,
      .energy-mode-value,
      .energy-mode-code,
      .energy-mode-definition { min-width: 0; max-width: 100%; overflow-wrap: anywhere }
      .energy-mode-label { font-size: clamp(5.4px,1.6vw,6.2px); letter-spacing: 0 }
      .energy-mode-value { justify-items: center; overflow: hidden }
      .energy-mode-code {
        font-size: clamp(14px,4vw,17px); font-weight: 950; line-height: 1; text-align: center; white-space: normal;
      }
      .energy-mode-definition { font-size: clamp(5.2px,1.5vw,5.8px) }
      .energy-battery, .energy-grid, .energy-generator { padding-inline: 2px }
      .energy-battery-icon {
        left: auto; right: 4%; top: 8px; bottom: 8px; width: 44%; height: auto;
      }
      .energy-battery .energy-node-register { left: 4px; right: 52%; text-align: left }
      .energy-battery-values {
        left: 4%; right: auto; width: 44%; font-size: 11px; text-align: left;
      }
      .energy-battery .flow-direction {
        left: 4%; right: auto; width: 44%; text-align: left;
      }
      .energy-node.energy-solar .energy-solar-values,
      .energy-node.energy-inverter .energy-inverter-values,
      .energy-node.energy-home .energy-home-values,
      .energy-node.energy-grid .energy-grid-values,
      .energy-node.energy-generator .energy-generator-values {
        left: 50%; right: auto; width: calc(100% - 12px);
        color: var(--text); font-size: 19px; font-weight: 950; line-height: 1;
        text-align: center; text-shadow: 0 1px 2px var(--card-start), 0 0 3px var(--card-start);
        transform: translate(-50%,-50%);
      }
      .energy-node.energy-battery .energy-battery-values {
        left: 4%; right: auto; width: 44%;
        color: var(--text); font-size: 19px; font-weight: 950; line-height: 1;
        text-align: left; text-shadow: 0 1px 2px var(--card-start), 0 0 3px var(--card-start);
        transform: translateY(-50%);
      }
      .flow-direction { left: 3px; right: 3px; bottom: 6px; font-size: 7px }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        scroll-behavior: auto !important;
        transition-duration: .01ms !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
      }
      html.demo-energy-flow .flow-connector.active .flow-line {
        animation-duration: var(--flow-duration,1.4s) !important;
        animation-iteration-count: infinite !important;
        animation-play-state: running !important;
      }
      html.demo-energy-flow .flow-connector.active .flow-line { animation-name: energy-track !important }
    }
  </style>
</head>
<body>
  <script>
    // Fail-safe: never leave the interface hidden if later startup code fails.
    window.setTimeout(() => document.documentElement.classList.remove('booting'), 2000);
  </script>
  <main class="shell">
    <header>
      <div class="brand">
        <div class="logo">☀</div>
        <div><h1>Solar Inverter Web</h1><div class="subtitle" id="identifier" data-i18n="waitingInverter">Очікування даних інвертора…</div></div>
      </div>
      <div class="header-actions">
        <label class="theme-switch">
          <input id="theme-toggle" type="checkbox" role="switch" aria-label="Увімкнути світлу тему" data-i18n-aria="themeAria">
          <span class="theme-slider" aria-hidden="true"></span>
          <span id="theme-name">Темна</span>
        </label>
        <div class="language-switch" role="group" aria-label="Мова інтерфейсу" data-i18n-aria="languageAria">
          <button class="language-option active" type="button" data-language="uk" aria-pressed="true">УКР</button>
          <button class="language-option" type="button" data-language="ru" aria-pressed="false">РУС</button>
          <button class="language-option" type="button" data-language="en" aria-pressed="false">ENG</button>
        </div>
        <button id="register-map-upload-button" type="button" data-i18n="uploadRegisterMap" data-i18n-title="registerMapHelp">↑ Завантажити карту CSV</button>
        <input id="register-map-file" type="file" accept=".csv,text/csv" aria-label="Завантажити карту регістрів CSV" data-i18n-aria="uploadRegisterMap" hidden>
        <button id="app-toggle" type="button">Зупинити моніторинг</button>
        <div class="view-tabs" role="tablist" aria-label="Розділи" data-i18n-aria="viewTabsAria">
          <button class="view-tab active" id="dashboard-tab" type="button" role="tab" data-view="dashboard" aria-selected="true" data-i18n="dashboardTab">Панель</button>
          <button class="view-tab" id="charts-tab" type="button" role="tab" data-view="charts" aria-selected="false" data-i18n="chartsTab">Графіки</button>
          <button class="view-tab" id="lcd-tab" type="button" role="tab" data-view="lcd" aria-selected="false" data-i18n="lcdTab">LCD</button>
        </div>
        <div class="status" id="status"><span class="dot"></span><span class="status-label">НЕМАЄ ЗВ’ЯЗКУ</span></div>
      </div>
    </header>

    <section id="dashboard-view">
    <div class="toolbar">
      <label class="chip"><span data-i18n="requestEvery">Запит кожні</span>&nbsp;
        <select id="poll-rate" aria-label="Інтервал опитування" data-i18n-aria="pollAria">
          <option value="0" data-i18n="interval05">0.5 с</option><option value="1" data-i18n="interval1">1 с</option>
          <option value="2" data-i18n="interval2">2 с</option><option value="3" data-i18n="interval5">5 с</option><option value="4" data-i18n="interval10">10 с</option>
        </select>
      </label>
      <label class="chip"><span data-i18n="readMode">Режим читання</span>&nbsp;
        <select id="read-mode" aria-label="Режим читання" data-i18n-aria="readModeAria">
          <option value="fast" data-i18n="fast">Швидкий</option><option value="compatible" data-i18n="compatible">Сумісний</option>
        </select>
      </label>
      <button id="demo-button" class="all-data-demo-button" type="button">Запустити реалістичне демо на 120 с</button>
      <button id="manage-values-button" type="button" data-i18n="addValues">＋ Додати індикатори</button>
      <span class="chip" id="cycle">Цикл —</span>
      <span class="chip" id="site-visits">Відвідувачі — · —</span>
      <span class="chip updated" id="updated">Ще не оновлено</span>
    </div>

    <div class="panel error" id="error"></div>
    <article class="energy-flow-card" id="energy-flow-card" aria-label="Потік енергії" data-i18n-aria="energyFlowAria">
      <div class="energy-flow-head">
        <h2 data-i18n="energyFlowTitle">Потік енергії</h2>
        <span class="energy-flow-status" id="energy-flow-status">—</span>
      </div>
      <div class="energy-flow-scroll" tabindex="0" aria-label="Схема потоків енергії" data-i18n-aria="energyFlowAria">
      <div class="energy-flow-diagram">
        <div class="energy-node energy-solar" id="energy-solar-node">
          <span class="energy-node-icon" aria-hidden="true">&#9728;</span>
          <span class="energy-node-register" id="energy-solar-registers">—</span>
          <span class="energy-node-label" data-i18n="solarPanels">Сонячні панелі</span>
          <span class="energy-node-value energy-solar-values">
            <span id="energy-solar-voltage">— V</span>
            <span id="energy-solar-power">— W</span>
            <span id="energy-solar-current">— A</span>
          </span>
          <span class="flow-direction" id="energy-solar-direction"></span>
        </div>
        <div class="flow-connector flow-pv" id="energy-pv-flow" aria-hidden="true">
          <svg class="flow-lines" viewBox="0 0 100 100" preserveAspectRatio="none" focusable="false">
            <line class="flow-line flow-line-desktop" x1="0" y1="50" x2="100" y2="50"/>
            <line class="flow-line flow-line-mobile" x1="50" y1="0" x2="50" y2="100"/>
          </svg>
        </div>
        <div class="energy-node energy-inverter" id="energy-inverter-node">
          <span class="energy-node-icon energy-node-image-icon" aria-hidden="true"></span>
          <span class="energy-node-register" id="energy-inverter-registers">—</span>
          <span class="energy-node-label" data-i18n="inverter">Інвертор</span>
          <span class="energy-inverter-load" id="energy-inverter-load">— %</span>
          <span class="energy-node-value energy-inverter-values">
            <span class="energy-inverter-fan-row" id="energy-inverter-fan-row">
              <svg class="energy-inverter-fan-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" stroke-width="1.4" opacity=".7"/>
                <path fill="currentColor" d="M11.1 9.8C8.9 7.1 9.2 3.4 11.7 2.7c2.1-.5 3.5 2.8 1.5 6.9-.5 1-1.4 1.1-2.1.2Zm3.1 1.3c2.7-2.2 6.4-1.9 7.1.6.5 2.1-2.8 3.5-6.9 1.5-1-.5-1.1-1.4-.2-2.1Zm-1.3 3.1c2.2 2.7 1.9 6.4-.6 7.1-2.1.5-3.5-2.8-1.5-6.9.5-1 1.4-1.1 2.1-.2Zm-3.1-1.3c-2.7 2.2-6.4 1.9-7.1-.6-.5-2.1 2.8-3.5 6.9-1.5 1 .5 1.1 1.4.2 2.1Z"/>
                <circle cx="12" cy="12" r="2.1" fill="var(--card-start)" stroke="currentColor" stroke-width="1.2"/>
              </svg>
              <span data-i18n="inverterFanSpeed">Швидкість вентилятора</span>
              <strong class="energy-inverter-fan-value" id="energy-inverter-fan-speed">— %</strong>
            </span>
            <span class="energy-mode-row"><span class="energy-mode-label" data-i18n="outputMode">Режим AC</span><span class="energy-mode-value"><strong class="energy-mode-code" id="energy-inverter-ac-mode">—</strong><small class="energy-mode-definition" id="energy-inverter-ac-definition"></small></span></span>
            <span class="energy-mode-row"><span class="energy-mode-label" data-i18n="inputMode">Джерело входу</span><span class="energy-mode-value"><strong class="energy-mode-code" id="energy-inverter-input-mode">—</strong><small class="energy-mode-definition" id="energy-inverter-input-definition"></small></span></span>
            <span class="energy-mode-row"><span class="energy-mode-label" data-i18n="chargeMode">Режим батареї</span><span class="energy-mode-value"><strong class="energy-mode-code" id="energy-inverter-charge-mode">—</strong><small class="energy-mode-definition" id="energy-inverter-charge-definition"></small></span></span>
          </span>
          <span class="flow-direction" aria-hidden="true"></span>
        </div>
        <div class="flow-connector flow-home" id="energy-home-flow" aria-hidden="true">
          <svg class="flow-lines" viewBox="0 0 100 100" preserveAspectRatio="none" focusable="false">
            <line class="flow-line flow-line-desktop" x1="0" y1="50" x2="100" y2="50"/>
            <line class="flow-line flow-line-mobile" x1="0" y1="100" x2="100" y2="0"/>
          </svg>
        </div>
        <div class="flow-connector flow-generator" id="energy-generator-flow" aria-hidden="true">
          <svg class="flow-lines" viewBox="0 0 100 100" preserveAspectRatio="none" focusable="false">
            <line class="flow-line flow-line-desktop" x1="0" y1="0" x2="100" y2="100"/>
            <line class="flow-line flow-line-mobile" x1="0" y1="0" x2="100" y2="100"/>
          </svg>
        </div>
        <div class="energy-node energy-generator" id="energy-generator-node">
          <span class="energy-node-icon energy-node-image-icon" aria-hidden="true"></span>
          <span class="energy-node-register" id="energy-generator-registers">—</span>
          <span class="energy-node-label" data-i18n="generator">Генератор</span>
          <span class="energy-node-value energy-generator-values" hidden>
            <span id="energy-generator-power">— W</span>
            <span id="energy-generator-current">— A</span>
            <span id="energy-generator-voltage">— V</span>
          </span>
          <span class="flow-direction" id="energy-generator-direction"></span>
        </div>
        <div class="energy-node energy-home" id="energy-home-node">
          <span class="energy-node-icon energy-node-image-icon" aria-hidden="true"></span>
          <span class="energy-node-register" id="energy-home-registers">—</span>
          <span class="energy-node-label" data-i18n="home">Дім</span>
          <span class="energy-node-value energy-home-values">
            <span id="energy-home-current">— A</span>
            <span id="energy-home-power">— W</span>
            <span id="energy-home-voltage">— V</span>
          </span>
          <span class="flow-direction" id="energy-home-direction"></span>
        </div>
        <div class="energy-node energy-grid" id="energy-grid-node">
          <span class="energy-node-icon energy-node-image-icon" aria-hidden="true"></span>
          <span class="energy-node-register" id="energy-grid-registers">—</span>
          <span class="energy-node-label" data-i18n="grid">Мережа</span>
          <span class="energy-node-value energy-grid-values">
            <span id="energy-grid-power">— W</span>
            <span id="energy-grid-current">— A</span>
            <span id="energy-grid-voltage">— V</span>
          </span>
          <span class="flow-direction" id="energy-grid-direction"></span>
        </div>
        <div class="flow-connector flow-grid" id="energy-grid-flow" aria-hidden="true">
          <svg class="flow-lines" viewBox="0 0 100 100" preserveAspectRatio="none" focusable="false">
            <line class="flow-line flow-line-desktop" x1="50" y1="0" x2="50" y2="100"/>
            <line class="flow-line flow-line-mobile" x1="50" y1="0" x2="50" y2="100"/>
          </svg>
        </div>
        <div class="flow-connector flow-battery" id="energy-battery-flow" aria-hidden="true">
          <svg class="flow-lines" viewBox="0 0 100 100" preserveAspectRatio="none" focusable="false">
            <line class="flow-line flow-line-desktop" x1="0" y1="100" x2="100" y2="0"/>
            <line class="flow-line flow-line-mobile" x1="100" y1="50" x2="0" y2="50"/>
          </svg>
        </div>
        <div class="energy-node energy-battery" id="energy-battery-node">
          <span class="energy-node-icon energy-battery-icon" id="energy-battery-icon" role="img">
            <span class="energy-battery-fill" aria-hidden="true"></span>
            <span class="energy-battery-percent" id="energy-battery-percent" aria-hidden="true">—</span>
          </span>
          <span class="energy-node-register" id="energy-battery-registers">—</span>
          <span class="energy-node-label" data-i18n="battery">Батарея</span>
          <span class="energy-node-value energy-battery-values">
            <span id="energy-battery-current">— A</span>
            <span id="energy-battery-power">— W</span>
            <span id="energy-battery-voltage">— V</span>
          </span>
          <span class="flow-direction" id="energy-battery-direction"></span>
        </div>
      </div>
      </div>
    </article>
    <section class="panel solar-energy-panel" aria-label="Вироблена сонячна енергія" data-i18n-aria="solarEnergyAria">
      <div class="solar-energy-head">
        <h2 data-i18n="solarEnergyTitle">Вироблена сонячна енергія</h2>
        <span class="solar-energy-note" data-i18n="solarEnergyEstimate">Підтверджено: R153 + R156</span>
      </div>
      <div class="solar-energy-grid">
        <article class="solar-energy-total"><span class="solar-energy-period" data-i18n="today">Сьогодні</span><span class="solar-energy-value" id="solar-energy-today">—</span></article>
        <article class="solar-energy-total"><span class="solar-energy-period" data-i18n="thisWeek">Цього тижня</span><span class="solar-energy-value" id="solar-energy-week">—</span></article>
        <article class="solar-energy-total"><span class="solar-energy-period" data-i18n="thisMonth">Цього місяця</span><span class="solar-energy-value" id="solar-energy-month">—</span></article>
        <article class="solar-energy-total"><span class="solar-energy-period" data-i18n="thisYear">Цього року</span><span class="solar-energy-value" id="solar-energy-year">—</span></article>
      </div>
      <div class="solar-energy-error" id="solar-energy-error" hidden></div>
    </section>
    <div class="dashboard-gauge-toolbar" id="dashboard-gauge-toolbar" hidden>
      <button id="dashboard-clear-gauges" class="clear-selection" type="button" data-i18n="clearDashboard">Очистити панель</button>
    </div>
    <section class="gauges" id="gauges" aria-label="Індикатори інвертора" data-i18n-aria="gaugesAria"></section>

    <section class="panel register-logger">
      <div class="logger-layout">
        <div class="logger-copy">
          <h2 data-i18n="registerLogger">Журнал змін регістрів</h2>
          <div class="muted" data-i18n="registerLoggerHelp">Після запуску фіксує зміни регістрів від фізичних кнопок у CSV: швидке опитування 0,5 с та час Мадрида.</div>
          <div class="logger-status" id="register-log-status" aria-live="polite">Запис не запущено</div>
        </div>
        <div class="logger-actions">
          <input class="logger-note" id="register-log-note" type="text" maxlength="500" placeholder="Напр. панелі вимкнено" data-i18n-placeholder="registerLogNotePlaceholder" disabled>
          <button id="register-log-mark" type="button" data-i18n="markRegisterLog" disabled>＋ Додати позначку</button>
          <button id="register-log-start" type="button" data-i18n="startRegisterLog">● Почати запис</button>
          <button id="register-log-stop" type="button" data-i18n="stopRegisterLog" disabled>■ Зупинити</button>
          <a class="logger-download" id="register-log-download" href="/api/register-log/download" data-i18n="downloadRegisterLog" hidden>↓ Завантажити CSV</a>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div><h2 data-i18n="liveRegisters">Поточні регістри</h2><span class="muted" id="register-count"></span></div>
        <input id="search" type="search" placeholder="Пошук регістрів…" aria-label="Пошук регістрів" data-i18n-placeholder="searchRegisters" data-i18n-aria="searchRegisters">
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th data-i18n="register">Регістр</th><th data-i18n="group">Група</th><th data-i18n="name">Назва</th><th data-i18n="value">Значення</th><th data-i18n="raw">Сире</th></tr></thead>
          <tbody id="registers"></tbody>
        </table>
      </div>
    </section>
    </section>

    <section id="lcd-view" hidden>
      <div class="panel lcd-panel">
        <div class="lcd-screen">
          <div class="lcd-head">
            <div><h2 data-i18n="lcdTitle">LCD ІНВЕРТОРА</h2><div class="lcd-subtitle" data-i18n="lcdSubtitle">Поточні показники з Modbus</div></div>
            <span class="lcd-mode" id="lcd-mode">—</span>
          </div>
          <div class="lcd-flow">
            <div class="lcd-node" id="lcd-grid-node"><span class="lcd-node-icon">∿</span><span class="lcd-node-label" data-i18n="grid">Мережа</span><span class="lcd-node-value" id="lcd-grid">—</span></div>
            <div class="lcd-arrow" id="lcd-grid-arrow">→</div>
            <div class="lcd-node" id="lcd-inverter-node"><span class="lcd-node-icon">▣</span><span class="lcd-node-label" data-i18n="inverter">Інвертор</span><span class="lcd-node-value" id="lcd-power">—</span></div>
            <div class="lcd-arrow" id="lcd-load-arrow">→</div>
            <div class="lcd-node" id="lcd-load-node"><span class="lcd-node-icon">⌂</span><span class="lcd-node-label" data-i18n="load">Навантаження</span><span class="lcd-node-value" id="lcd-load">—</span></div>
          </div>
          <div class="lcd-main">
            <div class="lcd-primary" id="lcd-ac-output-card"><span class="lcd-primary-label" data-i18n="acOutputCurrent">Вихідний струм AC</span><span class="lcd-primary-value" id="lcd-ac-output-current">—</span></div>
            <div class="lcd-primary" id="lcd-battery-card"><span class="lcd-primary-label" data-i18n="batteryVoltage">Напруга батареї</span><span class="lcd-primary-value" id="lcd-battery-voltage">—</span></div>
            <div class="lcd-primary" id="lcd-soc-card"><span class="lcd-primary-label" data-i18n="batterySoc">Заряд батареї</span><span class="lcd-primary-value" id="lcd-soc">—</span></div>
          </div>
          <div class="lcd-readouts">
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="gridVoltage">Напруга мережі</span><span class="lcd-readout-value" id="lcd-grid-voltage">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="frequency">Частота</span><span class="lcd-readout-value" id="lcd-frequency">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="gridCurrent">Струм мережі</span><span class="lcd-readout-value" id="lcd-grid-current">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="gridPower">Потужність мережі</span><span class="lcd-readout-value" id="lcd-grid-power">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="inverterLoad">Завантаження інвертора</span><span class="lcd-readout-value" id="lcd-inverter-load">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="loadPower">Активна потужність навантаження</span><span class="lcd-readout-value" id="lcd-load-power">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="apparentLoadPower">Повна потужність навантаження</span><span class="lcd-readout-value" id="lcd-apparent-load-power">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="gridLowVoltageThreshold">Нижній поріг напруги мережі</span><span class="lcd-readout-value" id="lcd-grid-low-voltage-threshold">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="batteryCurrent">Струм батареї</span><span class="lcd-readout-value" id="lcd-battery-current">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="batteryPower">Потужність батареї</span><span class="lcd-readout-value" id="lcd-battery-power">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="inverterTemperature">Температура інвертора</span><span class="lcd-readout-value" id="lcd-temperature">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="maxChargeVoltage">Макс. напруга заряду</span><span class="lcd-readout-value" id="lcd-charge-voltage">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="currentLimit">Дозволений тривалий струм розряду</span><span class="lcd-readout-value" id="lcd-current-limit">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="lowSocThreshold">Нижній поріг SOC</span><span class="lcd-readout-value" id="lcd-low-soc-threshold">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="batteryState">Стан батареї</span><span class="lcd-readout-value" id="lcd-battery-state">—</span></div>
            <div class="lcd-readout"><span class="lcd-readout-label" data-i18n="systemStatus">Стан системи</span><span class="lcd-readout-value" id="lcd-system-status">—</span></div>
          </div>
          <div class="lcd-status-line" id="lcd-status-line">—</div>
          <div class="lcd-page-panel" aria-live="polite">
            <div class="lcd-page-head"><span class="lcd-page-code" id="lcd-page-code">LCD</span><span class="lcd-page-title" id="lcd-page-title">—</span></div>
            <div class="lcd-page-values">
              <div class="lcd-page-reading" id="lcd-page-reading-1"><span class="lcd-readout-label" id="lcd-page-label-1">—</span><span class="lcd-readout-value" id="lcd-page-value-1">—</span></div>
              <div class="lcd-page-reading" id="lcd-page-reading-2"><span class="lcd-readout-label" id="lcd-page-label-2">—</span><span class="lcd-readout-value" id="lcd-page-value-2">—</span></div>
            </div>
            <div class="lcd-page-description" id="lcd-page-description">—</div>
          </div>
          <div class="lcd-controls-wrap">
            <div class="lcd-controls-title" data-i18n="lcdControls">Керування LCD</div>
            <div class="lcd-controls" role="group" aria-label="Керування LCD" data-i18n-aria="lcdControls">
              <button class="lcd-key" type="button" data-lcd-key="escape" data-i18n-aria="lcdEscapeAria">ESC</button>
              <button class="lcd-key" type="button" data-lcd-key="up" data-i18n-aria="lcdUpAria">▲ UP</button>
              <button class="lcd-key" type="button" data-lcd-key="down" data-i18n-aria="lcdDownAria">▼ DOWN</button>
              <button class="lcd-key" type="button" data-lcd-key="enter" data-i18n-aria="lcdEnterAria">ENTER</button>
            </div>
            <div class="lcd-controls-note" data-i18n="lcdControlsLocalOnly">Віртуальні клавіші керують лише сторінками застосунку. У демо активний CSV-журнал фіксує кожне натискання. Налаштування інвертора не змінюються.</div>
          </div>
        </div>
      </div>
    </section>

    <section id="charts-view" hidden>
      <div class="charts-layout">
        <aside class="panel chart-selector">
          <h2 data-i18n="availableValues">Доступні значення</h2>
          <div class="muted" data-i18n="selectionHelp">Кожен вибраний показник додається на панель і до графіків у реальному часі.</div>
          <input id="chart-search" type="search" placeholder="Пошук значень…" aria-label="Пошук значень графіка" data-i18n-placeholder="searchValues" data-i18n-aria="searchChartValues">
          <div class="chart-selector-actions">
            <button id="chart-select-all" type="button" data-i18n="selectAllGauges" disabled>Вибрати всі</button>
            <button id="chart-clear-all" class="clear-selection" type="button" data-i18n="clearAllGauges" disabled>Очистити всі</button>
          </div>
          <div class="value-list" id="chart-value-list"></div>
        </aside>
        <div class="charts-main">
          <div class="panel-head charts-head">
            <div>
              <h2 data-i18n="liveCharts">Графіки в реальному часі</h2>
              <span class="muted" id="chart-selection-count">Значення не вибрано</span>
            </div>
            <button id="chart-demo-button" class="all-data-demo-button" type="button">Запустити реалістичне демо на 120 с</button>
          </div>
          <div class="chart-grid" id="chart-grid">
            <div class="chart-empty">Виберіть значення зі списку, щоб запустити графіки в реальному часі.</div>
          </div>
        </div>
      </div>
    </section>

    <dialog class="gauge-picker" id="gauge-picker">
      <div class="gauge-picker-head">
        <div>
          <h2 data-i18n="chooseGauges">Choose gauges</h2>
          <div class="muted" data-i18n="gaugePickerHelp">Вибрані індикатори з’являться на панелі та у графіках.</div>
        </div>
        <button class="gauge-picker-close" type="button" data-close-gauge-picker aria-label="Закрити" data-i18n-aria="close">×</button>
      </div>
      <input class="gauge-picker-search" id="gauge-picker-search" type="search" placeholder="Пошук значень…" data-i18n-placeholder="searchValues" aria-label="Пошук значень" data-i18n-aria="searchValues">
      <div class="gauge-picker-actions">
        <button id="select-all-gauges" type="button" data-i18n="selectAllGauges" disabled>Вибрати всі</button>
        <button id="clear-all-gauges" class="clear-selection" type="button" data-i18n="clearDashboard" disabled>Очистити панель</button>
      </div>
      <div class="gauge-picker-list" id="gauge-picker-list"></div>
    </dialog>
  </main>
  <script>
    const colours = ['#38bdf8','#22d3ee','#34d399','#fbbf24','#a78bfa','#fb7185','#60a5fa'];
    const UI_TRANSLATIONS = {
      uk: {
        waitingInverter: 'Очікування даних інвертора…',
        themeAria: 'Увімкнути світлу тему',
        languageAria: 'Мова інтерфейсу',
        uploadRegisterMap: '↑ Завантажити карту CSV', registerMapHelp: 'CSV: register,name,unit,scale,display. Змінює лише відображення; Modbus не записується.',
        registerMapUploading: 'Завантаження…', registerMapUploaded: 'Карту застосовано: {count}',
        registerMapUploadError: 'Помилка CSV: {error}', registerMapFileTooLarge: 'CSV має бути не більшим за 1 МіБ',
        themeDark: 'Темна', themeLight: 'Світла',
        stopMonitoring: 'Зупинити моніторинг', startMonitoring: 'Запустити моніторинг',
        viewCharts: 'Переглянути графіки', dashboard: '← Панель',
        viewTabsAria: 'Розділи застосунку', dashboardTab: 'Панель', chartsTab: 'Графіки', lcdTab: 'LCD',
        lcdTitle: 'LCD ІНВЕРТОРА', lcdSubtitle: 'Поточні показники з Modbus',
        grid: 'Мережа', generator: 'Генератор', inverter: 'Інвертор', load: 'Навантаження', pvInput: 'Вхід PV',
        energyFlowTitle: 'Потік енергії', energyFlowAria: 'Поточний потік енергії між сонячними панелями, міською мережею або генератором, інвертором, батареєю та домом',
        solarPanels: 'Сонячні панелі', home: 'Дім', battery: 'Батарея', cityGenerator: 'Місто / Генератор',
        gridReady: 'МЕРЕЖА ДОСТУПНА',
        supplying: 'ВІДДАЄ', gridSupplying: 'ЖИВИТЬ ІНВЕРТОР', receiving: 'ОТРИМУЄ', consuming: 'СПОЖИВАЄ',
        outputMode: 'Пріоритет виходу', inputMode: 'Джерело входу', chargeMode: 'Пріоритет заряду',
        modeGridShort: 'Мережа першою', modeSolarShort: 'PV першими', modeGpbShort: 'Мережа першою · батарея резерв', modePgbShort: 'PV → мережа → батарея',
        modePbgShort: 'PV → батарея → мережа', modeMksShort: 'Пріоритет генератора',
        modeAppShort: 'Широкий діапазон AC', modeUpsShort: 'Стабільний вхід UPS', modeGenShort: 'Вхід генератора',
        modePngShort: 'Заряд від PV і мережі', modeOpvShort: 'Заряд лише від PV', modePvfShort: 'PV першими, мережа резерв',
        modeGridInputShort: 'Мережа живить інвертор', modeBatteryInputShort: 'Батарея живить інвертор', modeGeneratorInputShort: 'Генератор живить інвертор',
        demoSolarChargeExport: 'ДЕМО · PV → ДІМ + БАТ.',
        demoGridHome: 'ДЕМО · МЕРЕЖА → ДІМ', demoBatteryHome: 'ДЕМО · БАТ. → ДІМ',
        demoSolarExport: 'ДЕМО · PV → ДІМ', demoGeneratorHome: 'ДЕМО · ГЕНЕРАТОР → ІНВЕРТОР → ДІМ',
        demoMixedSources: 'ДЕМО · PV + БАТ. → ДІМ · МЕРЕЖІ НЕМАЄ',
        solarEnergyTitle: 'Вироблена сонячна енергія', solarEnergyAria: 'Підсумки виробленої сонячної енергії',
        solarEnergyEstimate: 'Підтверджено: потужність PV з R153 + R156',
        today: 'Сьогодні', thisWeek: 'Цього тижня', thisMonth: 'Цього місяця', thisYear: 'Цього року',
        waitingSolar: 'ОЧІКУЄ PV',
        batteryVoltage: 'Напруга батареї', batterySoc: 'Заряд батареї', frequency: 'Частота',
        gridVoltage: 'Напруга мережі', gridCurrent: 'Струм мережі', gridPower: 'Потужність мережі',
        pvPower: 'Потужність PV', loadPower: 'Активна потужність навантаження', apparentLoadPower: 'Повна потужність навантаження', loadPowerFactor: 'Коефіцієнт потужності',
        acOutputCurrent: 'Вихідний струм AC', inverterLoad: 'Завантаження інвертора', inverterFanSpeed: 'Швидкість вентилятора', gridLowVoltageThreshold: 'Нижній поріг напруги мережі',
        batteryCurrent: 'Струм батареї', batteryPower: 'Потужність батареї', batteryTemperature: 'Температура батареї', inverterTemperature: 'Температура інвертора', lowSocThreshold: 'Нижній поріг SOC',
        maxChargeVoltage: 'Макс. напруга заряду', currentLimit: 'Дозволений тривалий струм розряду', batteryState: 'Стан батареї',
        r413BmsFormula: '85% BMS · налаштування ≈ {value} A',
        systemStatus: 'Стан системи',
        charging: 'ЗАРЯДЖАННЯ', discharging: 'РОЗРЯДЖАННЯ', batteryIdle: 'НЕАКТИВНО',
        lcdControls: 'Керування LCD', lcdEscapeAria: 'Повернутися на головний екран LCD',
        lcdUpAria: 'Попередня інформаційна сторінка LCD', lcdDownAria: 'Наступна інформаційна сторінка LCD',
        lcdEnterAria: 'Відкрити вибрану сторінку LCD',
        lcdControlsLocalOnly: 'Віртуальні клавіші керують лише сторінками застосунку. У демо активний CSV-журнал фіксує кожне натискання. Налаштування інвертора не змінюються.',
        mainDisplay: 'Головний екран', dailyPvEnergy: 'Сонячна енергія за день', totalPvEnergy: 'Загальна сонячна енергія',
        availableCapacity: 'Поточна ємність батареї', possibleBatteryHealth: 'SOH батареї', lowerBmsVoltageLimit: 'Нижня межа напруги BMS',
        alarmFault: 'Стан BMS', alarmFlags: 'Прапорці стану BMS', bmsConnection: 'Зв’язок із BMS',
        deviceInformation: 'Інформація про пристрій', protocolVersion: 'Версія протоколу, старше слово', deviceConfiguration: 'Версія протоколу, молодше слово',
        lcdMainPageHelp: 'UP і DOWN перемикають інформаційні сторінки P1–P26, включно з телеметрією V1.31.',
        lcdP1Help: 'P1 показує денне вироблення. Якщо значення Modbus недоступне, використовується розраховане значення з локальної SQLite.',
        lcdP2Help: 'P2 показує загальне вироблення. Якщо значення Modbus недоступне, використовується накопичене значення з локальної SQLite.',
        lcdP3Help: 'P3 показує напругу та струм літієвої батареї.', lcdP4Help: 'P4 показує температуру та SOC літієвої батареї.',
        lcdP5Help: 'P5 показує поточну ємність батареї R409 та SOH батареї R408.', lcdP6Help: 'P6 показує максимальну напругу заряду та нижню межу напруги BMS.',
        lcdP7Help: 'P7 показує дозволений тривалий струм розряджання батареї R413 та нижній поріг SOC.', lcdP8Help: 'P8 показує зв’язок із BMS та прапорці стану BMS.',
        lcdP9Help: 'P9 показує старше та молодше слова версії протоколу з R17 і R18.', lcdV131Help: 'Додаткова інформаційна сторінка телеметрії Modbus V1.31. Значення доступні лише для читання.', settingsReadOnly: 'Режим налаштувань недоступний: інструкція не містить безпечних Modbus-адрес для запису.',
        offline: 'НЕМАЄ ЗВ’ЯЗКУ', online: 'У МЕРЕЖІ', notConnected: 'НЕ ПІДКЛЮЧЕНО', paused: 'ПРИЗУПИНЕНО', demoMode: 'ДЕМО',
        requestEvery: 'Запит кожні', pollAria: 'Інтервал опитування',
        interval05: '0.5 с', interval1: '1 с', interval2: '2 с', interval5: '5 с', interval10: '10 с',
        readMode: 'Режим читання', readModeAria: 'Режим читання',
        fast: 'Швидкий', compatible: 'Сумісний',
        runDemo: 'Запустити реалістичне демо на 120 с',
        stopDemo: '■ Зупинити · {elapsed} / {seconds} с · {count} значень',
        addValues: '＋ Додати індикатори',
        registerLogger: 'Журнал змін регістрів',
        registerLoggerHelp: 'Після запуску фіксує зміни регістрів від фізичних кнопок у CSV: швидке опитування 0,5 с та час Мадрида.',
        registerLogNotePlaceholder: 'Напр. панелі вимкнено', markRegisterLog: '＋ Додати позначку',
        startRegisterLog: '● Почати запис', stopRegisterLog: '■ Зупинити',
        downloadRegisterLog: '↓ Завантажити CSV', registerLogIdle: 'Запис не запущено',
        registerLogActive: 'Запис · {filename} · рядків: {changes} · {size}',
        registerLogStopped: 'Зупинено · {filename} · рядків: {changes} · {size}',
        registerLogStorage: 'вільно: {free} · видалено старих журналів: {count}',
        registerLogPhysicalCapture: 'захоплення фізичних кнопок · {seconds} с',
        registerLogError: 'Помилка журналу: {error}', registerLogRequestError: 'Не вдалося змінити стан журналу: {error}',
        cycleInitial: 'Цикл —', visitorsInitial: 'Відвідувачі — · —',
        notUpdated: 'Ще не оновлено', gaugesAria: 'Індикатори інвертора',
        addedValues: 'Додані індикатори панелі', liveRegisters: 'Поточні регістри',
        searchRegisters: 'Пошук регістрів…',
        register: 'Регістр', group: 'Група', name: 'Назва', value: 'Значення', raw: 'Сире',
        registerNumber: 'Регістр {number}', operatingStatusCode: 'Код робочого стану {number}',
        availableValues: 'Доступні значення',
        selectionHelp: 'Кожен вибраний показник додається на панель і до графіків у реальному часі.',
        searchValues: 'Пошук значень…', searchChartValues: 'Пошук значень графіка',
        liveCharts: 'Графіки в реальному часі', noValuesSelected: 'Значення не вибрано',
        selectValues: 'Виберіть значення зі списку, щоб запустити графіки в реальному часі.',
        dashboardChart: 'Панель + графік', removeDashboard: 'Видалити з панелі',
        emptyDashboard: 'Індикатори не вибрано. Натисніть «Додати індикатори» та виберіть значення.',
        dragGauge: 'Перетягніть, щоб змінити порядок',
        chooseGauges: 'Виберіть індикатори', gaugePickerHelp: 'Вибрані індикатори з’являться на панелі й у графіках.',
        addGauge: 'Додати індикатор', clearDashboard: 'Очистити панель', selectAllGauges: 'Вибрати всі', clearAllGauges: 'Очистити всі', close: 'Закрити',
        selectedSummary: 'Вибрано значень: {count} · останні 2 хвилини',
        chartAria: 'Графік у реальному часі для {label}',
        waiting: 'Очікування…', noData: 'Немає даних',
        registerCount: 'Отримано: {available} · очікують даних: {waiting} · показано: {shown}',
        unknownDevice: 'Невідомий пристрій', updated: 'Оновлено {time}',
        cyclePaused: 'Цикл {cycle} · моніторинг призупинено',
        cycleReads: 'Цикл {cycle} · {seconds} с · зчитано: {reads}',
        visitors: 'Відвідувачі {count} · {date}',
        connectionError: 'Помилка підключення: {error}',
        connectionLost: 'Втрачено зв’язок із панеллю: {error}',
        unitValue: 'значення', gaugeDetail: '{unit} · регістр R{register}',
        allDataDemo: 'Реалістичне демо даних', direct: 'прямий перехід',
        visitConsole: '[Відвідування Solar Inverter Web]',
        totalVisitorsLabel: 'усього відвідувачів', dateLabel: 'дата', openedLabel: 'відкрито',
        referrerLabel: 'джерело переходу', browserLanguageLabel: 'мова браузера',
        browserLabel: 'браузер', viewportLabel: 'розмір вікна'
      },
      ru: {
        waitingInverter: 'Ожидание данных инвертора…',
        themeAria: 'Включить светлую тему',
        languageAria: 'Язык интерфейса',
        uploadRegisterMap: '↑ Загрузить карту CSV', registerMapHelp: 'CSV: register,name,unit,scale,display. Меняет только отображение; запись Modbus не выполняется.',
        registerMapUploading: 'Загрузка…', registerMapUploaded: 'Карта применена: {count}',
        registerMapUploadError: 'Ошибка CSV: {error}', registerMapFileTooLarge: 'CSV должен быть не больше 1 МиБ',
        themeDark: 'Тёмная', themeLight: 'Светлая',
        stopMonitoring: 'Остановить мониторинг', startMonitoring: 'Запустить мониторинг',
        viewCharts: 'Просмотреть графики', dashboard: '← Панель',
        viewTabsAria: 'Разделы приложения', dashboardTab: 'Панель', chartsTab: 'Графики', lcdTab: 'LCD',
        lcdTitle: 'LCD ИНВЕРТОРА', lcdSubtitle: 'Текущие показатели из Modbus',
        grid: 'Сеть', generator: 'Генератор', inverter: 'Инвертор', load: 'Нагрузка', pvInput: 'Вход PV',
        energyFlowTitle: 'Поток энергии', energyFlowAria: 'Текущий поток энергии между солнечными панелями, городской сетью или генератором, инвертором, батареей и домом',
        solarPanels: 'Солнечные панели', home: 'Дом', battery: 'Батарея', cityGenerator: 'Сеть / Генератор',
        gridReady: 'СЕТЬ ДОСТУПНА',
        supplying: 'ОТДАЁТ', gridSupplying: 'ПИТАЕТ ИНВЕРТОР', receiving: 'ПОЛУЧАЕТ', consuming: 'ПОТРЕБЛЯЕТ',
        outputMode: 'Приоритет выхода', inputMode: 'Источник входа', chargeMode: 'Приоритет заряда',
        modeGridShort: 'Сеть первой', modeSolarShort: 'PV первыми', modeGpbShort: 'Сеть первой · батарея резерв', modePgbShort: 'PV → сеть → батарея',
        modePbgShort: 'PV → батарея → сеть', modeMksShort: 'Приоритет генератора',
        modeAppShort: 'Широкий диапазон AC', modeUpsShort: 'Стабильный вход UPS', modeGenShort: 'Вход генератора',
        modePngShort: 'Заряд от PV и сети', modeOpvShort: 'Заряд только от PV', modePvfShort: 'PV сначала, сеть резерв',
        modeGridInputShort: 'Сеть питает инвертор', modeBatteryInputShort: 'Батарея питает инвертор', modeGeneratorInputShort: 'Генератор питает инвертор',
        demoSolarChargeExport: 'ДЕМО · PV → ДОМ + БАТ.',
        demoGridHome: 'ДЕМО · СЕТЬ → ДОМ', demoBatteryHome: 'ДЕМО · БАТ. → ДОМ',
        demoSolarExport: 'ДЕМО · PV → ДОМ', demoGeneratorHome: 'ДЕМО · ГЕНЕРАТОР → ИНВЕРТОР → ДОМ',
        demoMixedSources: 'ДЕМО · PV + БАТ. → ДОМ · СЕТИ НЕТ',
        solarEnergyTitle: 'Выработанная солнечная энергия', solarEnergyAria: 'Итоги выработанной солнечной энергии',
        solarEnergyEstimate: 'Подтверждено: мощность PV из R153 + R156',
        today: 'Сегодня', thisWeek: 'На этой неделе', thisMonth: 'В этом месяце', thisYear: 'В этом году',
        waitingSolar: 'ОЖИДАЕТ PV',
        batteryVoltage: 'Напряжение батареи', batterySoc: 'Заряд батареи', frequency: 'Частота',
        gridVoltage: 'Напряжение сети', gridCurrent: 'Ток сети', gridPower: 'Мощность сети',
        pvPower: 'Мощность PV', loadPower: 'Активная мощность нагрузки', apparentLoadPower: 'Полная мощность нагрузки', loadPowerFactor: 'Коэффициент мощности',
        acOutputCurrent: 'Выходной ток AC', inverterLoad: 'Загрузка инвертора', inverterFanSpeed: 'Скорость вентилятора', gridLowVoltageThreshold: 'Нижний порог напряжения сети',
        batteryCurrent: 'Ток батареи', batteryPower: 'Мощность батареи', batteryTemperature: 'Температура батареи', inverterTemperature: 'Температура инвертора', lowSocThreshold: 'Нижний порог SOC',
        maxChargeVoltage: 'Макс. напряжение заряда', currentLimit: 'Разрешённый длительный ток разряда', batteryState: 'Состояние батареи',
        r413BmsFormula: '85% BMS · настройка ≈ {value} A',
        systemStatus: 'Состояние системы',
        charging: 'ЗАРЯДКА', discharging: 'РАЗРЯДКА', batteryIdle: 'НЕАКТИВНО',
        lcdControls: 'Управление LCD', lcdEscapeAria: 'Вернуться на главный экран LCD',
        lcdUpAria: 'Предыдущая информационная страница LCD', lcdDownAria: 'Следующая информационная страница LCD',
        lcdEnterAria: 'Открыть выбранную страницу LCD',
        lcdControlsLocalOnly: 'Виртуальные клавиши управляют только страницами приложения. В демо активный CSV-журнал фиксирует каждое нажатие. Настройки инвертора не изменяются.',
        mainDisplay: 'Главный экран', dailyPvEnergy: 'Солнечная энергия за день', totalPvEnergy: 'Общая солнечная энергия',
        availableCapacity: 'Текущая ёмкость батареи', possibleBatteryHealth: 'SOH батареи', lowerBmsVoltageLimit: 'Нижний предел напряжения BMS',
        alarmFault: 'Состояние BMS', alarmFlags: 'Флаги состояния BMS', bmsConnection: 'Связь с BMS',
        deviceInformation: 'Информация об устройстве', protocolVersion: 'Версия протокола, старшее слово', deviceConfiguration: 'Версия протокола, младшее слово',
        lcdMainPageHelp: 'UP и DOWN переключают информационные страницы P1–P26, включая телеметрию V1.31.',
        lcdP1Help: 'P1 показывает дневную выработку. Если значение Modbus недоступно, используется расчётное значение из локальной SQLite.',
        lcdP2Help: 'P2 показывает общую выработку. Если значение Modbus недоступно, используется накопленное значение из локальной SQLite.',
        lcdP3Help: 'P3 показывает напряжение и ток литиевой батареи.', lcdP4Help: 'P4 показывает температуру и SOC литиевой батареи.',
        lcdP5Help: 'P5 показывает текущую ёмкость батареи R409 и SOH батареи R408.', lcdP6Help: 'P6 показывает максимальное напряжение заряда и нижний предел напряжения BMS.',
        lcdP7Help: 'P7 показывает разрешённый продолжительный ток разряда АКБ R413 и нижний порог SOC.', lcdP8Help: 'P8 показывает связь с BMS и флаги состояния BMS.',
        lcdP9Help: 'P9 показывает старшее и младшее слова версии протокола из R17 и R18.', lcdV131Help: 'Дополнительная информационная страница телеметрии Modbus V1.31. Значения доступны только для чтения.', settingsReadOnly: 'Режим настроек недоступен: инструкция не содержит безопасных Modbus-адресов для записи.',
        offline: 'НЕТ СВЯЗИ', online: 'В СЕТИ', notConnected: 'НЕ ПОДКЛЮЧЕНО', paused: 'ПРИОСТАНОВЛЕНО', demoMode: 'ДЕМО',
        requestEvery: 'Запрос каждые', pollAria: 'Интервал опроса',
        interval05: '0.5 с', interval1: '1 с', interval2: '2 с', interval5: '5 с', interval10: '10 с',
        readMode: 'Режим чтения', readModeAria: 'Режим чтения',
        fast: 'Быстрый', compatible: 'Совместимый',
        runDemo: 'Запустить реалистичное демо на 120 с',
        stopDemo: '■ Остановить · {elapsed} / {seconds} с · {count} значений',
        addValues: '＋ Добавить индикаторы',
        registerLogger: 'Журнал изменений регистров',
        registerLoggerHelp: 'После запуска фиксирует изменения регистров от физических кнопок в CSV: быстрый опрос 0,5 с и время Мадрида.',
        registerLogNotePlaceholder: 'Напр. панели выключены', markRegisterLog: '＋ Добавить отметку',
        startRegisterLog: '● Начать запись', stopRegisterLog: '■ Остановить',
        downloadRegisterLog: '↓ Скачать CSV', registerLogIdle: 'Запись не запущена',
        registerLogActive: 'Запись · {filename} · строк: {changes} · {size}',
        registerLogStopped: 'Остановлено · {filename} · строк: {changes} · {size}',
        registerLogStorage: 'свободно: {free} · удалено старых журналов: {count}',
        registerLogPhysicalCapture: 'захват физических кнопок · {seconds} с',
        registerLogError: 'Ошибка журнала: {error}', registerLogRequestError: 'Не удалось изменить журнал: {error}',
        cycleInitial: 'Цикл —', visitorsInitial: 'Посетители — · —',
        notUpdated: 'Ещё не обновлено', gaugesAria: 'Индикаторы инвертора',
        addedValues: 'Добавленные индикаторы панели', liveRegisters: 'Текущие регистры',
        searchRegisters: 'Поиск регистров…',
        register: 'Регистр', group: 'Группа', name: 'Название', value: 'Значение', raw: 'Сырое',
        registerNumber: 'Регистр {number}', operatingStatusCode: 'Код рабочего состояния {number}',
        availableValues: 'Доступные значения',
        selectionHelp: 'Каждый выбранный показатель добавляется на панель и на графики в реальном времени.',
        searchValues: 'Поиск значений…', searchChartValues: 'Поиск значений графика',
        liveCharts: 'Графики в реальном времени', noValuesSelected: 'Значения не выбраны',
        selectValues: 'Выберите значения из списка, чтобы запустить графики в реальном времени.',
        dashboardChart: 'Панель + график', removeDashboard: 'Удалить с панели',
        emptyDashboard: 'Индикаторы не выбраны. Нажмите «Добавить индикаторы» и выберите значения.',
        dragGauge: 'Перетащите, чтобы изменить порядок',
        chooseGauges: 'Выберите индикаторы', gaugePickerHelp: 'Выбранные индикаторы появятся на панели и на графиках.',
        addGauge: 'Добавить индикатор', clearDashboard: 'Очистить панель', selectAllGauges: 'Выбрать все', clearAllGauges: 'Очистить все', close: 'Закрыть',
        selectedSummary: 'Выбрано значений: {count} · последние 2 минуты',
        chartAria: 'График в реальном времени для {label}',
        waiting: 'Ожидание…', noData: 'Нет данных',
        registerCount: 'Получено: {available} · ожидают данных: {waiting} · показано: {shown}',
        unknownDevice: 'Неизвестное устройство', updated: 'Обновлено {time}',
        cyclePaused: 'Цикл {cycle} · мониторинг приостановлен',
        cycleReads: 'Цикл {cycle} · {seconds} с · считано: {reads}',
        visitors: 'Посетители {count} · {date}',
        connectionError: 'Ошибка подключения: {error}',
        connectionLost: 'Потеряна связь с панелью: {error}',
        unitValue: 'значение', gaugeDetail: '{unit} · регистр R{register}',
        allDataDemo: 'Реалистичное демо данных', direct: 'прямой переход',
        visitConsole: '[Посещение Solar Inverter Web]',
        totalVisitorsLabel: 'всего посетителей', dateLabel: 'дата', openedLabel: 'открыто',
        referrerLabel: 'источник перехода', browserLanguageLabel: 'язык браузера',
        browserLabel: 'браузер', viewportLabel: 'размер окна'
      },
      en: {
        waitingInverter: 'Waiting for inverter data…',
        themeAria: 'Use light theme',
        languageAria: 'Interface language',
        uploadRegisterMap: '↑ Upload CSV map', registerMapHelp: 'CSV: register,name,unit,scale,display. Changes presentation only; Modbus is never written.',
        registerMapUploading: 'Uploading…', registerMapUploaded: 'Map applied: {count}',
        registerMapUploadError: 'CSV error: {error}', registerMapFileTooLarge: 'CSV must be no larger than 1 MiB',
        themeDark: 'Dark', themeLight: 'Light',
        stopMonitoring: 'Stop monitoring', startMonitoring: 'Start monitoring',
        viewCharts: 'View charts', dashboard: '← Dashboard',
        viewTabsAria: 'Application sections', dashboardTab: 'Dashboard', chartsTab: 'Charts', lcdTab: 'LCD',
        lcdTitle: 'INVERTER LCD', lcdSubtitle: 'Live readings from Modbus',
        grid: 'Grid', generator: 'Generator', inverter: 'Inverter', load: 'Load', pvInput: 'PV input',
        energyFlowTitle: 'Energy flow', energyFlowAria: 'Current energy flow between the solar panels, city grid or generator, inverter, battery, and home',
        solarPanels: 'Solar panels', home: 'Home', battery: 'Battery', cityGenerator: 'Grid / Generator',
        gridReady: 'GRID AVAILABLE',
        supplying: 'SUPPLYING', gridSupplying: 'SUPPLIES INVERTER', receiving: 'RECEIVING', consuming: 'CONSUMING',
        outputMode: 'Output priority', inputMode: 'Input source', chargeMode: 'Charge priority',
        modeGridShort: 'Grid first', modeSolarShort: 'PV first', modeGpbShort: 'Grid first · battery reserve', modePgbShort: 'PV → grid → battery',
        modePbgShort: 'PV → battery → grid', modeMksShort: 'Generator priority',
        modeAppShort: 'Wide AC range', modeUpsShort: 'Stable UPS input', modeGenShort: 'Generator input',
        modePngShort: 'PV and grid charge', modeOpvShort: 'PV charging only', modePvfShort: 'PV first, grid backup',
        modeGridInputShort: 'Grid supplies inverter', modeBatteryInputShort: 'Battery supplies inverter', modeGeneratorInputShort: 'Generator supplies inverter',
        demoSolarChargeExport: 'DEMO · PV → HOME + BAT.',
        demoGridHome: 'DEMO · GRID → HOME', demoBatteryHome: 'DEMO · BAT. → HOME',
        demoSolarExport: 'DEMO · PV → HOME', demoGeneratorHome: 'DEMO · GENERATOR → INVERTER → HOME',
        demoMixedSources: 'DEMO · PV + BAT. → HOME · GRID OFF',
        solarEnergyTitle: 'Solar energy generated', solarEnergyAria: 'Generated solar energy totals',
        solarEnergyEstimate: 'Confirmed: PV power from R153 + R156',
        today: 'Today', thisWeek: 'This week', thisMonth: 'This month', thisYear: 'This year',
        waitingSolar: 'WAITING FOR PV',
        batteryVoltage: 'Battery voltage', batterySoc: 'Battery charge', frequency: 'Frequency',
        gridVoltage: 'Grid voltage', gridCurrent: 'Grid current', gridPower: 'Grid power',
        pvPower: 'PV power', loadPower: 'Active load power', apparentLoadPower: 'Apparent load power', loadPowerFactor: 'Power factor',
        acOutputCurrent: 'AC output current', inverterLoad: 'Inverter load', inverterFanSpeed: 'Fan speed', gridLowVoltageThreshold: 'Grid low-voltage threshold',
        batteryCurrent: 'Battery current', batteryPower: 'Battery power', batteryTemperature: 'Battery temperature', inverterTemperature: 'Inverter temperature', lowSocThreshold: 'Low SOC threshold',
        maxChargeVoltage: 'Max. charge voltage', currentLimit: 'Permitted continuous discharge current', batteryState: 'Battery state',
        r413BmsFormula: '85% BMS · setting ≈ {value} A',
        systemStatus: 'System status',
        charging: 'CHARGING', discharging: 'DISCHARGING', batteryIdle: 'IDLE',
        lcdControls: 'LCD controls', lcdEscapeAria: 'Return to the main LCD screen',
        lcdUpAria: 'Previous LCD information page', lcdDownAria: 'Next LCD information page',
        lcdEnterAria: 'Open the selected LCD page',
        lcdControlsLocalOnly: 'The virtual keys control app pages only. During demo, an active CSV log records every press. Inverter settings are not changed.',
        mainDisplay: 'Main display', dailyPvEnergy: 'Daily solar energy', totalPvEnergy: 'Total solar energy',
        availableCapacity: 'Current battery capacity', possibleBatteryHealth: 'Battery SOH', lowerBmsVoltageLimit: 'Lower BMS voltage limit',
        alarmFault: 'BMS status', alarmFlags: 'BMS status flags', bmsConnection: 'BMS connection',
        deviceInformation: 'Device information', protocolVersion: 'Protocol version, high word', deviceConfiguration: 'Protocol version, low word',
        lcdMainPageHelp: 'UP and DOWN browse information pages P1–P26, including V1.31 telemetry.',
        lcdP1Help: 'P1 shows daily production. When no Modbus value is available, it uses the calculated value from local SQLite.',
        lcdP2Help: 'P2 shows total production. When no Modbus value is available, it uses the accumulated value from local SQLite.',
        lcdP3Help: 'P3 shows lithium-battery voltage and current.', lcdP4Help: 'P4 shows lithium-battery temperature and SOC.',
        lcdP5Help: 'P5 shows current battery capacity R409 and battery SOH R408.', lcdP6Help: 'P6 shows maximum charge voltage and the lower BMS voltage limit.',
        lcdP7Help: 'P7 shows permitted continuous battery discharge current R413 and the low SOC threshold.', lcdP8Help: 'P8 shows BMS communication and BMS status flags.',
        lcdP9Help: 'P9 shows the high and low words of the protocol version from R17 and R18.', lcdV131Help: 'Additional Modbus V1.31 telemetry page. Values are read-only.', settingsReadOnly: 'Settings mode is unavailable because the manual provides no safe Modbus write addresses.',
        offline: 'OFFLINE', online: 'ONLINE', notConnected: 'NOT CONNECTED', paused: 'PAUSED', demoMode: 'DEMO',
        requestEvery: 'Request every', pollAria: 'Polling interval',
        interval05: '0.5 s', interval1: '1 s', interval2: '2 s', interval5: '5 s', interval10: '10 s',
        readMode: 'Read mode', readModeAria: 'Read mode',
        fast: 'Fast', compatible: 'Compatible',
        runDemo: 'Run realistic 120s demo',
        stopDemo: '■ Stop · {elapsed} / {seconds}s · {count} values',
        addValues: '＋ Add gauges',
        registerLogger: 'Register change log',
        registerLoggerHelp: 'After starting, captures register changes caused by physical buttons in CSV using fast 0.5-second polling and Madrid time.',
        registerLogNotePlaceholder: 'E.g. panels switched off', markRegisterLog: '＋ Add marker',
        startRegisterLog: '● Start recording', stopRegisterLog: '■ Stop',
        downloadRegisterLog: '↓ Download CSV', registerLogIdle: 'Recording is not running',
        registerLogActive: 'Recording · {filename} · rows: {changes} · {size}',
        registerLogStopped: 'Stopped · {filename} · rows: {changes} · {size}',
        registerLogStorage: 'free: {free} · old logs removed: {count}',
        registerLogPhysicalCapture: 'physical-button capture · {seconds} s',
        registerLogError: 'Log error: {error}', registerLogRequestError: 'Could not change log state: {error}',
        cycleInitial: 'Cycle —', visitorsInitial: 'Visitors — · —',
        notUpdated: 'Not updated yet', gaugesAria: 'Live inverter gauges',
        addedValues: 'Added dashboard gauges', liveRegisters: 'Live registers',
        searchRegisters: 'Search registers…',
        register: 'Register', group: 'Group', name: 'Name', value: 'Value', raw: 'Raw',
        registerNumber: 'Register {number}', operatingStatusCode: 'Operating status code {number}',
        availableValues: 'Available values',
        selectionHelp: 'Each selected reading is added to the dashboard and live charts.',
        searchValues: 'Search values…', searchChartValues: 'Search chart values',
        liveCharts: 'Live charts', noValuesSelected: 'No values selected',
        selectValues: 'Select values from the list to start real-time charts.',
        dashboardChart: 'Dashboard + chart', removeDashboard: 'Remove from dashboard',
        emptyDashboard: 'No gauges selected. Click Add gauges and select the readings to display.',
        dragGauge: 'Drag to reorder',
        chooseGauges: 'Choose gauges', gaugePickerHelp: 'Selected gauges appear on the dashboard and live charts.',
        addGauge: 'Add gauge', clearDashboard: 'Clear dashboard', selectAllGauges: 'Select all', clearAllGauges: 'Clear all', close: 'Close',
        selectedSummary: '{count} values selected · last 2 minutes',
        chartAria: 'Live chart for {label}',
        waiting: 'Waiting…', noData: 'No data',
        registerCount: '{available} received · {waiting} awaiting data · {shown} shown',
        unknownDevice: 'Unknown device', updated: 'Updated {time}',
        cyclePaused: 'Cycle {cycle} · monitoring paused',
        cycleReads: 'Cycle {cycle} · {seconds} s · {reads} reads',
        visitors: 'Visitors {count} · {date}',
        connectionError: 'Connection error: {error}',
        connectionLost: 'Dashboard connection lost: {error}',
        unitValue: 'value', gaugeDetail: '{unit} · register R{register}',
        allDataDemo: 'Realistic data demo', direct: 'direct',
        visitConsole: '[Solar Inverter Web visit]',
        totalVisitorsLabel: 'total visitors', dateLabel: 'date', openedLabel: 'opened',
        referrerLabel: 'referrer', browserLanguageLabel: 'browser language',
        browserLabel: 'browser', viewportLabel: 'viewport'
      }
    };
    const DATA_TRANSLATIONS = {
      'AC': {ru:'AC', en:'AC'},
      'BMS': {ru:'BMS', en:'BMS'},
      'PV': {ru:'PV', en:'PV'},
      'Ідентифікація': {ru:'Идентификация', en:'Identification'},
      'Ідентифікатор пристрою, слово 1': {ru:'Идентификатор устройства, слово 1', en:'Device identifier, word 1'},
      'Ідентифікатор пристрою, слово 2': {ru:'Идентификатор устройства, слово 2', en:'Device identifier, word 2'},
      'Ідентифікатор пристрою, слово 3': {ru:'Идентификатор устройства, слово 3', en:'Device identifier, word 3'},
      'Ідентифікатор пристрою, слово 4': {ru:'Идентификатор устройства, слово 4', en:'Device identifier, word 4'},
      'Ідентифікатор пристрою, слово 5': {ru:'Идентификатор устройства, слово 5', en:'Device identifier, word 5'},
      'Ідентифікатор пристрою, слово 6': {ru:'Идентификатор устройства, слово 6', en:'Device identifier, word 6'},
      'Ідентифікатор пристрою, слово 7': {ru:'Идентификатор устройства, слово 7', en:'Device identifier, word 7'},
      'Ідентифікатор пристрою, слово 8': {ru:'Идентификатор устройства, слово 8', en:'Device identifier, word 8'},
      'Ідентифікатор пристрою, слово 9': {ru:'Идентификатор устройства, слово 9', en:'Device identifier, word 9'},
      'Код протоколу або версії': {ru:'Код протокола или версии', en:'Protocol or version code'},
      'Системне слово 27': {ru:'Системное слово 27', en:'System word 27'},
      'Системний прапорець 28': {ru:'Системный флаг 28', en:'System flag 28'},
      'Напруга зовнішньої мережі': {ru:'Напряжение внешней сети', en:'External grid voltage'},
      'Частота зовнішньої мережі': {ru:'Частота внешней сети', en:'External grid frequency'},
      'Активна потужність навантаження': {ru:'Активная мощность нагрузки', en:'Active load power'},
      'Повна потужність навантаження': {ru:'Полная мощность нагрузки', en:'Apparent load power'},
      'Рівень заряду акумулятора': {ru:'Уровень заряда аккумулятора', en:'Battery state of charge'},
      'Температура акумулятора': {ru:'Температура аккумулятора', en:'Battery temperature'},
      'Фактичний струм із мережі': {ru:'Фактический ток из сети', en:'Actual grid current'},
      'Фактична потужність мережі': {ru:'Фактическая мощность сети', en:'Actual grid power'},
      'Бітова маска можливостей або стану': {ru:'Битовая маска возможностей или состояния', en:'Capability or status bitmask'},
      'Системне слово 65': {ru:'Системное слово 65', en:'System word 65'},
      'Код конфігурації 66': {ru:'Код конфигурации 66', en:'Configuration code 66'},
      'Код конфігурації 67': {ru:'Код конфигурации 67', en:'Configuration code 67'},
      'Системне значення 68': {ru:'Системное значение 68', en:'System value 68'},
      'Упаковане знакове значення 69': {ru:'Упакованное знаковое значение 69', en:'Packed signed value 69'},
      'Номінальна або вихідна напруга AC': {ru:'Номинальное или выходное напряжение AC', en:'Nominal or output AC voltage'},
      'Вихідна напруга AC': {ru:'Выходное напряжение AC', en:'Output AC voltage'},
      'Вихідний струм AC': {ru:'Выходной ток AC', en:'Output AC current'},
      'Завантаження інвертора': {ru:'Загрузка инвертора', en:'Inverter load'},
      'Нижній поріг вхідної напруги мережі': {ru:'Нижний порог входного напряжения сети', en:'Grid input low-voltage threshold'},
      'Робочий режим інвертора': {ru:'Рабочий режим инвертора', en:'Inverter operating mode'},
      'Напруга акумулятора від BMS': {ru:'Напряжение аккумулятора от BMS', en:'Battery voltage from BMS'},
      'Струм акумулятора від BMS': {ru:'Ток аккумулятора от BMS', en:'Battery current from BMS'},
      'SOC від BMS': {ru:'SOC от BMS', en:'SOC from BMS'},
      'Максимальна напруга заряду BMS': {ru:'Максимальное напряжение заряда BMS', en:'BMS maximum charge voltage'},
      'Недоступне значення BMS 142': {ru:'Недоступное значение BMS 142', en:'Unavailable BMS value 142'},
      'Недоступне значення BMS 143': {ru:'Недоступное значение BMS 143', en:'Unavailable BMS value 143'},
      'Прапорці стану BMS': {ru:'Флаги состояния BMS', en:'BMS status flags'},
      'Непідтверджений параметр 145': {ru:'Неподтверждённый параметр 145', en:'Unconfirmed parameter 145'},
      'Активність BMS': {ru:'Активность BMS', en:'BMS activity'},
      'Тип або протокол BMS': {ru:'Тип или протокол BMS', en:'BMS type or protocol'},
      'Конфігурація BMS': {ru:'Конфигурация BMS', en:'BMS configuration'},
      'Стан BMS': {ru:'Состояние BMS', en:'BMS status'},
      'SOC акумулятора BMS': {ru:'SOC аккумулятора BMS', en:'BMS battery SOC'},
      'Невідомий динамічний параметр': {ru:'Неизвестный динамический параметр', en:'Unknown dynamic parameter'},
      'Напруга акумулятора BMS': {ru:'Напряжение аккумулятора BMS', en:'BMS battery voltage'},
      'Струм BMS, канал 1': {ru:'Ток BMS, канал 1', en:'BMS current, channel 1'},
      'Струм BMS, канал 2': {ru:'Ток BMS, канал 2', en:'BMS current, channel 2'},
      'Верхня межа напруги': {ru:'Верхний предел напряжения', en:'Upper voltage limit'},
      'Нижня межа напруги': {ru:'Нижний предел напряжения', en:'Lower voltage limit'},
      'Поріг низької напруги': {ru:'Порог низкого напряжения', en:'Low-voltage threshold'},
      'Невідомий знаковий параметр': {ru:'Неизвестный знаковый параметр', en:'Unknown signed parameter'},
      'Напруга заряду': {ru:'Напряжение заряда', en:'Charge voltage'},
      'Підтримувальна напруга': {ru:'Поддерживающее напряжение', en:'Float voltage'},
      'Максимальний струм заряду': {ru:'Максимальный ток заряда', en:'Maximum charge current'},
      'Додаткова межа струму заряду': {ru:'Дополнительный предел тока заряда', en:'Additional charge-current limit'},
      'Поріг високої напруги': {ru:'Порог высокого напряжения', en:'High-voltage threshold'},
      'Межа або номінальна потужність': {ru:'Предел или номинальная мощность', en:'Limit or rated power'},
      'Параметр обмеження потужності': {ru:'Параметр ограничения мощности', en:'Power-limiting parameter'},
      'Тип батареї або кількість модулів': {ru:'Тип батареи или число модулей', en:'Battery type or module count'},
      'Зв’язок із BMS': {ru:'Связь с BMS', en:'BMS communication'},
      'Напруга батареї': {ru:'Напряжение батареи', en:'Battery voltage'},
      'Струм батареї': {ru:'Ток батареи', en:'Battery current'},
      'Температура батареї': {ru:'Температура батареи', en:'Battery temperature'},
      'SOC батареї': {ru:'SOC батареи', en:'Battery SOC'},
      'SOH батареї': {ru:'SOH батареи', en:'Battery SOH'},
      'Недоступне значення 409': {ru:'Недоступное значение 409', en:'Unavailable value 409'},
      'Недоступне значення 410': {ru:'Недоступное значение 410', en:'Unavailable value 410'},
      'Максимальна напруга заряду': {ru:'Максимальное напряжение заряда', en:'Maximum charge voltage'},
      'Максимальний дозволений струм': {ru:'Максимальный разрешённый ток', en:'Maximum allowed current'},
      'Параметр ємності акумулятора': {ru:'Параметр ёмкости аккумулятора', en:'Battery capacity parameter'},
      'Резерв': {ru:'Резерв', en:'Reserved'},
      'Нижній поріг SOC': {ru:'Нижний порог SOC', en:'Low SOC threshold'},
      'Вихідна потужність AC': {ru:'Выходная мощность AC', en:'Output AC power'},
      'Температура': {ru:'Температура', en:'Temperature'},
      'Напруга акумулятора': {ru:'Напряжение аккумулятора', en:'Battery voltage'},
      'Струм акумулятора': {ru:'Ток аккумулятора', en:'Battery current'},
      'SOC акумулятора': {ru:'SOC аккумулятора', en:'Battery SOC'},
      'Потужність акумулятора': {ru:'Мощность аккумулятора', en:'Battery power'},
      'Режим входу інвертора': {ru:'Режим входа инвертора', en:'Inverter input mode'},
      'Режим виходу інвертора': {ru:'Режим выхода инвертора', en:'Inverter output mode'},
      'Режим заряджання інвертора': {ru:'Режим зарядки инвертора', en:'Inverter charging mode'},
      'Пріоритет вихідного джерела': {ru:'Приоритет выходного источника', en:'Output source priority'},
      'Режим входу AC': {ru:'Режим входа AC', en:'AC input mode'},
      'Пріоритет джерела заряджання': {ru:'Приоритет источника зарядки', en:'Charging source priority'},
      'Код верхнього аварійного порога частоти CA_HF1': {ru:'Код верхнего аварийного порога частоты CA_HF1', en:'Upper frequency fault-threshold code CA_HF1'},
      'Код верхнього аварійного порога частоти CA_HF2': {ru:'Код верхнего аварийного порога частоты CA_HF2', en:'Upper frequency fault-threshold code CA_HF2'},
      'Аварійний поріг частоти CA_LF1': {ru:'Аварийный порог частоты CA_LF1', en:'Frequency fault threshold CA_LF1'},
      'Аварійний поріг частоти CA_LF2': {ru:'Аварийный порог частоты CA_LF2', en:'Frequency fault threshold CA_LF2'},
      'Потужність': {ru:'Мощность', en:'Power'},
      'Середній поріг SOC': {ru:'Средний порог SOC', en:'Middle SOC threshold'},
      'Верхній поріг SOC': {ru:'Верхний порог SOC', en:'Upper SOC threshold'},
      'Регістр живої потужності PV не визначено; накопичення енергії призупинено': {ru:'Регистр фактической мощности PV не определён; накопление энергии приостановлено', en:'Live PV power register is not identified; energy accumulation is paused'},
      'Параметр системи 449': {ru:'Параметр системы 449', en:'System parameter 449'},
      'Упаковане значення 451': {ru:'Упакованное значение 451', en:'Packed value 451'},
      'Упаковане значення 453': {ru:'Упакованное значение 453', en:'Packed value 453'},
      'Упаковане знакове значення 455': {ru:'Упакованное знаковое значение 455', en:'Packed signed value 455'},
      'Напруга заряджання / ліміт': {ru:'Напряжение зарядки / предел', en:'Charging voltage / limit'},
      'Знаковий струмовий параметр': {ru:'Знаковый параметр тока', en:'Signed current parameter'},
      'Очікування або невідомий стан': {ru:'Ожидание или неизвестное состояние', en:'Standby or unknown state'},
      'Ймовірно робота від мережі або байпас': {ru:'Вероятно работа от сети или байпас', en:'Possibly grid or bypass operation'},
      'Ймовірно робота інвертора від батареї або PV': {ru:'Вероятно работа инвертора от батареи или PV', en:'Possibly inverter operation from battery or PV'},
      'Ймовірно заряджання або активна робота': {ru:'Вероятно зарядка или активная работа', en:'Possibly charging or active operation'},
      'Ймовірно помилка або аварійний стан': {ru:'Вероятно ошибка или аварийное состояние', en:'Possibly a fault or emergency state'},
      'нотатка не може бути порожньою': {ru:'заметка не может быть пустой', en:'note cannot be empty'},
      'нотатка не може перевищувати 500 символів': {ru:'заметка не может превышать 500 символов', en:'note cannot exceed 500 characters'},
      'спочатку запустіть запис журналу': {ru:'сначала запустите запись журнала', en:'start log recording first'},
      'action має бути start, stop або mark': {ru:'action должно быть start, stop или mark', en:'action must be start, stop, or mark'},
      'неправильний інтервал опитування': {ru:'неправильный интервал опроса', en:'invalid polling interval'},
      'неправильний режим читання': {ru:'неправильный режим чтения', en:'invalid read mode'},
      'paused має бути true або false': {ru:'paused должно быть true или false', en:'paused must be true or false'},
      'журнал ще не створено': {ru:'журнал ещё не создан', en:'log has not been created yet'},
      'Код протоколу/версії': {ru:'Код протокола/версии', en:'Protocol/version code'},
      'Код конфігурації пристрою': {ru:'Код конфигурации устройства', en:'Device configuration code'},
      'Слово прошивки/стану': {ru:'Слово прошивки/состояния', en:'Firmware/status word'},
      'Прапорець прошивки/стану': {ru:'Флаг прошивки/состояния', en:'Firmware/status flag'},
      'Бітова маска можливостей/стану': {ru:'Битовая маска возможностей/состояния', en:'Capability/status bitmask'},
      'Код конфігурації': {ru:'Код конфигурации', en:'Configuration code'},
      'Значення прошивки/стану': {ru:'Значение прошивки/состояния', en:'Firmware/status value'},
      'Знакове значення стану': {ru:'Знаковое значение состояния', en:'Signed status value'},
      'Напруга AC': {ru:'Напряжение AC', en:'AC voltage'},
      'Вхідний струм AC / значення навантаження': {ru:'Входной ток AC / значение нагрузки', en:'AC input current / load value'},
      'Частота AC': {ru:'Частота AC', en:'AC frequency'},
      'Напруга батареї (дані LCD)': {ru:'Напряжение батареи (данные LCD)', en:'Battery voltage (LCD data)'},
      'Відсоток заряду батареї/навантаження': {ru:'Процент заряда батареи/нагрузки', en:'Battery/load percentage'},
      'Напруга батареї': {ru:'Напряжение батареи', en:'Battery voltage'},
      'Струм заряджання батареї': {ru:'Ток зарядки батареи', en:'Battery charging current'},
      'Рівень заряду батареї': {ru:'Уровень заряда батареи', en:'Battery state of charge'},
      'Температура літієвої батареї': {ru:'Температура литиевой батареи', en:'Lithium battery temperature'},
      'Напруга літієвої батареї (P3)': {ru:'Напряжение литиевой батареи (P3)', en:'Lithium battery voltage (P3)'},
      'Струм літієвої батареї (P3)': {ru:'Ток литиевой батареи (P3)', en:'Lithium battery current (P3)'},
      'Рівень заряду літієвої батареї (P4)': {ru:'Уровень заряда литиевой батареи (P4)', en:'Lithium battery state of charge (P4)'},
      'Температура літієвої батареї (P4)': {ru:'Температура литиевой батареи (P4)', en:'Lithium battery temperature (P4)'},
      'Максимальна напруга заряджання літієвої батареї (P6)': {ru:'Максимальное напряжение зарядки литиевой батареи (P6)', en:'Maximum lithium battery charging voltage (P6)'},
      'Недоступне значення': {ru:'Недоступное значение', en:'Unavailable value'},
      'Потужність/струм/стан батареї': {ru:'Мощность/ток/состояние батареи', en:'Battery power/current/status'},
      'Код робочого стану': {ru:'Код рабочего состояния', en:'Operating status code'},
      'Стан/внутрішнє значення': {ru:'Состояние/внутреннее значение', en:'Status/internal value'},
      'Прапорець каналу/кількості BMS': {ru:'Флаг канала/количества BMS', en:'BMS channel/count flag'},
      'Код конфігурації BMS': {ru:'Код конфигурации BMS', en:'BMS configuration code'},
      'Код стану BMS': {ru:'Код состояния BMS', en:'BMS status code'},
      'Рівень заряду літієвої батареї': {ru:'Уровень заряда литиевой батареи', en:'Lithium battery state of charge'},
      'Вхідна напруга PV': {ru:'Входное напряжение PV', en:'PV input voltage'},
      'Напруга літієвої батареї': {ru:'Напряжение литиевой батареи', en:'Lithium battery voltage'},
      'Максимальний струм заряджання літієвої батареї': {ru:'Максимальный ток зарядки литиевой батареи', en:'Maximum lithium battery charging current'},
      'Струм літієвої батареї': {ru:'Ток литиевой батареи', en:'Lithium battery current'},
      'Межа напруги літієвої батареї': {ru:'Предел напряжения литиевой батареи', en:'Lithium battery voltage limit'},
      'Межа струму розряджання літієвої батареї': {ru:'Предел тока разрядки литиевой батареи', en:'Lithium battery discharge current limit'},
      'Налаштування напруги батареї': {ru:'Настройка напряжения батареи', en:'Battery voltage setting'},
      'Налаштування струму батареї': {ru:'Настройка тока батареи', en:'Battery current setting'},
      'Номінальна потужність / межа віддачі в мережу': {ru:'Номинальная мощность / предел отдачи в сеть', en:'Rated power / grid export limit'},
      'Налаштування потужності / межа': {ru:'Настройка мощности / предел', en:'Power setting / limit'},
      'Код BMS/стану': {ru:'Код BMS/состояния', en:'BMS/status code'},
      'Прапорець BMS/стану': {ru:'Флаг BMS/состояния', en:'BMS/status flag'},
      'Накопичене значення/потужність': {ru:'Накопленное значение/мощность', en:'Accumulated value/power'},
      'Залишкова/номінальна ємність літієвої батареї': {ru:'Оставшаяся/номинальная ёмкость литиевой батареи', en:'Remaining/rated lithium battery capacity'},
      'Максимальний струм літієвої батареї': {ru:'Максимальный ток литиевой батареи', en:'Maximum lithium battery current'},
      'Потужність батареї/PV': {ru:'Мощность батареи/PV', en:'Battery/PV power'},
      'Межа налаштування': {ru:'Предел настройки', en:'Setting limit'},
      'Напруга/значення': {ru:'Напряжение/значение', en:'Voltage/value'},
      'Упаковане значення/лічильник': {ru:'Упакованное значение/счётчик', en:'Packed value/counter'},
      'Упаковане знакове значення': {ru:'Упакованное знаковое значение', en:'Packed signed value'},
      'Струм батареї': {ru:'Ток батареи', en:'Battery current'},
      'Температура батареї': {ru:'Температура батареи', en:'Battery temperature'},
      'Стан батареї SOH / межа': {ru:'Состояние батареи SOH / предел', en:'Battery SOH / limit'},
      'Макс. напруга заряджання': {ru:'Макс. напряжение зарядки', en:'Max. charging voltage'},
      'Макс. струм заряджання': {ru:'Макс. ток зарядки', en:'Max. charging current'},
      'Межа струму розряджання': {ru:'Предел тока разрядки', en:'Discharge current limit'},
      'Потужність батареї / PV': {ru:'Мощность батареи / PV', en:'Battery / PV power'},
      'Номінальна потужність': {ru:'Номинальная мощность', en:'Rated power'},
      'Межа потужності': {ru:'Предел мощности', en:'Power limit'},
      'Система': {ru:'Система', en:'System'},
      'Батарея': {ru:'Батарея', en:'Battery'},
      'Налаштування': {ru:'Настройки', en:'Settings'},
      'Сире': {ru:'Сырое', en:'Raw'},
      'Робочий стан': {ru:'Рабочее состояние', en:'Operating status'},
      'Очікування / невідомо': {ru:'Ожидание / неизвестно', en:'Standby / unknown'},
      'Робота від мережі / байпас': {ru:'Работа от сети / байпас', en:'Grid / bypass operation'},
      'Робота інвертора від батареї або PV': {ru:'Работа инвертора от батареи или PV', en:'Inverter operation from battery or PV'},
      'Заряджання / активна робота': {ru:'Зарядка / активная работа', en:'Charging / active operation'},
      'Помилка або аварійний стан': {ru:'Ошибка или аварийное состояние', en:'Fault or emergency state'},
      'Немає даних mbpoll': {ru:'Нет данных mbpoll', en:'No mbpoll data'},
      'перевищено час очікування': {ru:'превышено время ожидания', en:'request timed out'},
      'mbpoll не знайдено': {ru:'mbpoll не найден', en:'mbpoll not found'},
      'помилка читання': {ru:'ошибка чтения', en:'read error'},
      'ніколи': {ru:'никогда', en:'never'},
      'Н/Д': {ru:'Н/Д', en:'N/A'},
      'Немає помилок або аварій': {ru:'Нет ошибок или аварий', en:'No faults or alarms'},
      'Випадкове демо всіх даних': {ru:'Случайное демо всех данных', en:'All-data random demo'}
    };
    Object.assign(DATA_TRANSLATIONS, {
      'Ідентифікатор пристрою, слово 10': {ru:'Идентификатор устройства, слово 10', en:'Device identifier, word 10'},
      'Режими': {ru:'Режимы', en:'Modes'}, 'Заряджання': {ru:'Зарядка', en:'Charging'}, 'Енергія': {ru:'Энергия', en:'Energy'},
      'Напруга мережі, фаза A': {ru:'Напряжение сети, фаза A', en:'Grid voltage, phase A'},
      'Струм мережі, фаза A': {ru:'Ток сети, фаза A', en:'Grid current, phase A'},
      'Частота мережі, фаза A': {ru:'Частота сети, фаза A', en:'Grid frequency, phase A'},
      'Потужність мережі, фаза A': {ru:'Мощность сети, фаза A', en:'Grid power, phase A'},
      'Вихідна напруга навантаження, фаза A': {ru:'Выходное напряжение нагрузки, фаза A', en:'Load output voltage, phase A'},
      'Вихідна частота AC': {ru:'Выходная частота AC', en:'AC output frequency'},
      'Напруга PV1': {ru:'Напряжение PV1', en:'PV1 voltage'}, 'Струм PV1': {ru:'Ток PV1', en:'PV1 current'},
      'Потужність PV1': {ru:'Мощность PV1', en:'PV1 power'}, 'Напруга PV2': {ru:'Напряжение PV2', en:'PV2 voltage'},
      'Струм PV2': {ru:'Ток PV2', en:'PV2 current'}, 'Потужність PV2': {ru:'Мощность PV2', en:'PV2 power'},
      'Енергія PV за сьогодні': {ru:'Энергия PV за сегодня', en:'PV energy today'},
      'Загальна енергія PV': {ru:'Общая энергия PV', en:'Total PV energy'},
      'Режим виходу': {ru:'Режим выхода', en:'Output mode'}, 'Паралельний режим': {ru:'Параллельный режим', en:'Parallel mode'},
      'Пріоритет виходу': {ru:'Приоритет выхода', en:'Output priority'}, 'Пріоритет заряджання': {ru:'Приоритет зарядки', en:'Charging priority'},
      'Стан автомата інвертора': {ru:'Состояние автомата инвертора', en:'Inverter state machine'},
      'Напруга позитивної DC-шини': {ru:'Напряжение положительной DC-шины', en:'Positive DC bus voltage'},
      'Напруга позитивної клеми батареї': {ru:'Напряжение положительной клеммы батареи', en:'Positive battery-terminal voltage'},
      'Струм розряджання батареї': {ru:'Ток разряда батареи', en:'Battery discharge current'},
      'Струм заряджання батареї': {ru:'Ток заряда батареи', en:'Battery charge current'},
      'Поріг сигналізації перенапруги': {ru:'Порог сигнализации перенапряжения', en:'Overvoltage alarm threshold'},
      'Поріг сигналізації низької напруги': {ru:'Порог сигнализации низкого напряжения', en:'Low-voltage alarm threshold'},
      'Напруга відсікання другого виходу': {ru:'Напряжение отсечки второго выхода', en:'Dual-output cutoff voltage'},
      'Час відсікання другого виходу': {ru:'Время отсечки второго выхода', en:'Dual-output cutoff time'},
      'Поточна ємність батареї': {ru:'Текущая ёмкость батареи', en:'Current battery capacity'},
      'Повна зарядна ємність батареї': {ru:'Полная зарядная ёмкость батареи', en:'Full-charge battery capacity'},
      'Максимальний струм заряджання BMS': {ru:'Максимальный ток заряда BMS', en:'BMS maximum charge current'},
      'Максимальний струм розряджання BMS': {ru:'Максимальный ток разряда BMS', en:'BMS maximum discharge current'},
      'Дозволений тривалий струм розряджання батареї': {ru:'Разрешённый продолжительный ток разряда АКБ', en:'Permitted continuous battery discharge current'},
      'Температура інвертора': {ru:'Температура инвертора', en:'Inverter temperature'},
      'Температура зарядного модуля': {ru:'Температура зарядного модуля', en:'Charger temperature'},
      'Нижній поріг напруги мережі': {ru:'Нижний порог напряжения сети', en:'Grid low-voltage threshold'},
      'Верхній поріг напруги мережі': {ru:'Верхний порог напряжения сети', en:'Grid high-voltage threshold'},
      'ID пакета BMS': {ru:'Идентификатор пакета BMS', en:'BMS packet ID'},
      'Ідентифікатор протоколу B': {ru:'Идентификатор протокола B', en:'Protocol B identifier'},
      'Інтервал вирівнювального заряджання': {ru:'Интервал выравнивающего заряда', en:'Equalisation charge interval'},
      'Версія ПЗ': {ru:'Версия ПО', en:'Firmware version'},
      'Версія ПЗ плати керування, молодше слово': {ru:'Версия ПО платы управления, младшее слово', en:'Control-board firmware version, low word'},
      'Версія ПЗ плати керування, старше слово': {ru:'Версия ПО платы управления, старшее слово', en:'Control-board firmware version, high word'},
      'Версія протоколу, молодше слово': {ru:'Версия протокола, младшее слово', en:'Protocol version, low word'},
      'Версія протоколу, старше слово': {ru:'Версия протокола, старшее слово', en:'Protocol version, high word'},
      'Вихідна активна потужність інвертора': {ru:'Выходная активная мощность инвертора', en:'Inverter output active power'},
      'Вихідна напруга інвертора': {ru:'Выходное напряжение инвертора', en:'Inverter output voltage'},
      'Вихідна повна потужність інвертора': {ru:'Выходная полная мощность инвертора', en:'Inverter output apparent power'},
      'Вихідна частота інвертора': {ru:'Выходная частота инвертора', en:'Inverter output frequency'},
      'Вихідний струм інвертора': {ru:'Выходной ток инвертора', en:'Inverter output current'},
      'Завантаження виходу інвертора': {ru:'Загрузка выхода инвертора', en:'Inverter output load'},
      'Затримка вирівнювального заряджання': {ru:'Задержка выравнивающего заряда', en:'Equalisation charge delay'},
      'Код несправності BMS': {ru:'Код неисправности BMS', en:'BMS fault code'},
      'Код попередження BMS': {ru:'Код предупреждения BMS', en:'BMS warning code'},
      'Максимальний струм заряджання': {ru:'Максимальный ток заряда', en:'Maximum charge current'},
      'Максимальний струм розряджання': {ru:'Максимальный ток разряда', en:'Maximum discharge current'},
      'Налаштована вихідна напруга': {ru:'Настроенное выходное напряжение', en:'Configured output voltage'},
      'Налаштована вихідна частота': {ru:'Настроенная выходная частота', en:'Configured output frequency'},
      'Напруга вирівнювального заряджання': {ru:'Напряжение выравнивающего заряда', en:'Equalisation charge voltage'},
      'Напруга від’ємної клеми батареї': {ru:'Напряжение отрицательной клеммы батареи', en:'Negative battery-terminal voltage'},
      'Напруга заряджання CV': {ru:'Напряжение заряда CV', en:'CV charge voltage'},
      'Напруга мережі': {ru:'Напряжение сети', en:'Grid voltage'},
      'Напруга мережі, детальний канал': {ru:'Напряжение сети, подробный канал', en:'Grid voltage, detailed channel'},
      'Напруга основного заряджання': {ru:'Напряжение основного заряда', en:'Bulk charge voltage'},
      'Напруга підтримувального заряджання': {ru:'Напряжение поддерживающего заряда', en:'Float charge voltage'},
      'Номінальна ємність BMS': {ru:'Номинальная ёмкость BMS', en:'BMS rated capacity'},
      'Повна ємність батареї': {ru:'Полная ёмкость батареи', en:'Full battery capacity'},
      'Помилка BMS': {ru:'Ошибка BMS', en:'BMS error'},
      'Поріг вимкнення батареї': {ru:'Порог отключения батареи', en:'Battery shutdown threshold'},
      'Поріг вимкнення за низьким SOC': {ru:'Порог отключения по низкому SOC', en:'Low-SOC shutdown threshold'},
      'Поріг низької напруги батареї': {ru:'Порог низкого напряжения батареи', en:'Battery low-voltage threshold'},
      'Поріг переходу батарея → AC': {ru:'Порог перехода батарея → AC', en:'Battery-to-AC transfer threshold'},
      'Поріг повернення AC → батарея': {ru:'Порог возврата AC → батарея', en:'AC-to-battery return threshold'},
      'Поріг попередження низького SOC': {ru:'Порог предупреждения о низком SOC', en:'Low-SOC warning threshold'},
      'Поточна ємність BMS': {ru:'Текущая ёмкость BMS', en:'BMS current capacity'},
      'Потужність мережі': {ru:'Мощность сети', en:'Grid power'},
      'Потужність мережі, детальний канал': {ru:'Мощность сети, подробный канал', en:'Grid power, detailed channel'},
      'Потужність споживання з мережі': {ru:'Потребляемая мощность из сети', en:'Power consumed from grid'},
      'Протокол зв’язку BMS (резерв)': {ru:'Протокол связи BMS (резерв)', en:'BMS communication protocol (reserved)'},
      'Пріоритет виходу (фактичний)': {ru:'Приоритет выхода (фактический)', en:'Output priority (actual)'},
      'Режим входу AC (фактичний)': {ru:'Режим входа AC (фактический)', en:'AC input mode (actual)'},
      'Резервний поріг відсікання високого SOC': {ru:'Резервный порог отсечки высокого SOC', en:'Reserved high-SOC cutoff threshold'},
      'Резервний поріг перемикання низького SOC': {ru:'Резервный порог переключения низкого SOC', en:'Reserved low-SOC switching threshold'},
      'Сигналізація BMS': {ru:'Сигнализация BMS', en:'BMS alarm'},
      'Стан вентилятора': {ru:'Состояние вентилятора', en:'Fan status'},
      'Стан енергетичних клем': {ru:'Состояние силовых клемм', en:'Power-terminal status'},
      'Стан заряджання': {ru:'Состояние зарядки', en:'Charging status'},
      'Стан зв’язку BMS': {ru:'Состояние связи BMS', en:'BMS communication status'},
      'Стан з’єднання BMS': {ru:'Состояние подключения BMS', en:'BMS connection status'},
      'Стан мережі літієвої батареї': {ru:'Состояние сети литиевой батареи', en:'Lithium-battery network status'},
      'Стан потоку енергії': {ru:'Состояние потока энергии', en:'Energy-flow status'},
      'Стан інвертора': {ru:'Состояние инвертора', en:'Inverter status'},
      'Струм від’ємної клеми батареї': {ru:'Ток отрицательной клеммы батареи', en:'Negative battery-terminal current'},
      'Струм заряджання CV': {ru:'Ток заряда CV', en:'CV charge current'},
      'Струм заряджання від AC': {ru:'Ток заряда от AC', en:'AC charging current'},
      'Струм мережі': {ru:'Ток сети', en:'Grid current'},
      'Струм мережі, детальний канал': {ru:'Ток сети, подробный канал', en:'Grid current, detailed channel'},
      'Струм підтримувального заряджання': {ru:'Ток поддерживающего заряда', en:'Float charge current'},
      'Температура PV': {ru:'Температура PV', en:'PV temperature'},
      'Температура акумулятора BMS': {ru:'Температура аккумулятора BMS', en:'BMS battery temperature'},
      'Температура довкілля': {ru:'Температура окружающей среды', en:'Ambient temperature'},
      'Температура зарядного модуля 2': {ru:'Температура зарядного модуля 2', en:'Charger module 2 temperature'},
      'Температура розрядного модуля': {ru:'Температура разрядного модуля', en:'Discharge-module temperature'},
      'Тип батареї': {ru:'Тип батареи', en:'Battery type'},
      'Точка постійної напруги BMS': {ru:'Точка постоянного напряжения BMS', en:'BMS constant-voltage point'},
      'Час вирівнювального заряджання': {ru:'Время выравнивающего заряда', en:'Equalisation charge duration'},
      'Частота мережі': {ru:'Частота сети', en:'Grid frequency'},
      'Частота мережі, детальний канал': {ru:'Частота сети, подробный канал', en:'Grid frequency, detailed channel'},
      'Швидкість вентилятора': {ru:'Скорость вентилятора', en:'Fan speed'},
      'Стан паралельної роботи': {ru:'Состояние параллельной работы', en:'Parallel status'},
      'Колір переднього RGB, старше слово': {ru:'Цвет переднего RGB, старшее слово', en:'RGB foreground colour, high word'},
      'Колір переднього RGB, молодше слово': {ru:'Цвет переднего RGB, младшее слово', en:'RGB foreground colour, low word'},
      'Режим переднього RGB': {ru:'Режим переднего RGB', en:'RGB foreground mode'},
      'Колір фонового RGB, старше слово': {ru:'Цвет фонового RGB, старшее слово', en:'RGB background colour, high word'},
      'Колір фонового RGB, молодше слово': {ru:'Цвет фонового RGB, младшее слово', en:'RGB background colour, low word'},
      'Режим фонового RGB': {ru:'Режим фонового RGB', en:'RGB background mode'},
      'Напруга генератора, фаза A': {ru:'Напряжение генератора, фаза A', en:'Generator voltage, phase A'},
      'Струм генератора, фаза A': {ru:'Ток генератора, фаза A', en:'Generator current, phase A'},
      'Частота генератора, фаза A': {ru:'Частота генератора, фаза A', en:'Generator frequency, phase A'},
      'Потужність генератора, фаза A': {ru:'Мощность генератора, фаза A', en:'Generator power, phase A'},
      'Навантаження мережі, фаза A': {ru:'Нагрузка сети, фаза A', en:'Grid load, phase A'},
      'Струм заряджання від PV1': {ru:'Ток зарядки от PV1', en:'PV1 charging current'},
      'Струм заряджання від PV2': {ru:'Ток зарядки от PV2', en:'PV2 charging current'},
      'Загальна потужність PV': {ru:'Общая мощность PV', en:'Total PV power'},
      'Енергія PV за місяць': {ru:'Энергия PV за месяц', en:'PV energy this month'},
      'Енергія PV за рік': {ru:'Энергия PV за год', en:'PV energy this year'},
      'Енергія': {ru:'Энергия', en:'Energy'},
      'Генератор': {ru:'Генератор', en:'Generator'},
      'Помилки': {ru:'Ошибки', en:'Faults'},
      'Потужність навантаження на виході, фаза A': {ru:'Мощность нагрузки на выходе, фаза A', en:'Output-side load power, phase A'},
      'Потужність навантаження на виході, фаза B': {ru:'Мощность нагрузки на выходе, фаза B', en:'Output-side load power, phase B'},
      'Потужність навантаження на виході, фаза C': {ru:'Мощность нагрузки на выходе, фаза C', en:'Output-side load power, phase C'},
      'Температура PV2': {ru:'Температура PV2', en:'PV2 temperature'}
    });
    for (const number of [1, 2]) {
      DATA_TRANSLATIONS[`Код несправності ${number}`] = {
        ru: `Код неисправности ${number}`,
        en: `Fault code ${number}`
      };
      DATA_TRANSLATIONS[`Код попередження ${number}`] = {
        ru: `Код предупреждения ${number}`,
        en: `Alarm code ${number}`
      };
    }
    for (const [ukName, ruName, enName] of [
      ['заряджання', 'зарядки', 'charging'],
      ['розряджання', 'разрядки', 'discharging'],
      ['інвертування', 'инвертирования', 'inverting'],
      ['навантаження', 'нагрузки', 'load'],
      ['віддачі в мережу', 'отдачи в сеть', 'grid feed-in'],
      ['споживання з мережі', 'потребления из сети', 'grid consumption']
    ]) {
      for (const [ukPeriod, ruPeriod, enPeriod] of [
        ['день', 'день', 'today'],
        ['місяць', 'месяц', 'this month'],
        ['рік', 'год', 'this year']
      ]) {
        DATA_TRANSLATIONS[`Енергія ${ukName} за ${ukPeriod}`] = {
          ru: `Энергия ${ruName} за ${ruPeriod}`,
          en: `${enName[0].toUpperCase()}${enName.slice(1)} energy ${enPeriod}`
        };
      }
      DATA_TRANSLATIONS[`Загальна енергія ${ukName}`] = {
        ru: `Общая энергия ${ruName}`,
        en: `Total ${enName} energy`
      };
    }
    for (const [periodUk, periodRu, periodEn] of [
      ['день', 'день', 'today'], ['місяць', 'месяц', 'month'],
      ['рік', 'год', 'year'], ['загальне', 'общее', 'total']
    ]) {
      const source = periodUk === 'загальне'
        ? 'Загальне споживання мережі'
        : `Споживання мережі за ${periodUk}`;
      const ru = periodUk === 'загальне'
        ? 'Общее потребление сети'
        : `Потребление сети за ${periodRu}`;
      const en = periodUk === 'загальне'
        ? 'Total grid consumption'
        : `Grid consumption ${periodEn}`;
      DATA_TRANSLATIONS[`${source}, старше слово`] = {ru: `${ru}, старшее слово`, en: `${en}, high word`};
      DATA_TRANSLATIONS[`${source}, молодше слово`] = {ru: `${ru}, младшее слово`, en: `${en}, low word`};
    }
    for (let register = 10; register <= 16; register += 1) {
      DATA_TRANSLATIONS[`Канал вимірювання зовнішньої мережі ${register}`] = {
        ru: `Канал измерения внешней сети ${register}`,
        en: `External grid measurement channel ${register}`
      };
    }
    for (const register of [131, 132, 135, 136]) {
      DATA_TRANSLATIONS[`Канал потужності або струму сонячного трекера ${register}`] = {
        ru: `Канал мощности или тока солнечного трекера ${register}`,
        en: `Solar tracker power or current channel ${register}`
      };
    }
    for (let register = 147; register <= 156; register += 1) {
      DATA_TRANSLATIONS[`Прапорець помилки або аварійного попередження ${register}`] = {
        ru: `Флаг ошибки или аварийного предупреждения ${register}`,
        en: `Fault or alarm warning flag ${register}`
      };
    }
    let currentLanguage = 'uk';
    function t(key, replacements = {}) {
      const template = UI_TRANSLATIONS[currentLanguage]?.[key] ?? UI_TRANSLATIONS.uk[key] ?? key;
      return template.replace(/\{(\w+)\}/g, (_, name) =>
        Object.prototype.hasOwnProperty.call(replacements, name) ? replacements[name] : `{${name}}`
      );
    }
    function localizeDataText(text) {
      if (!text || currentLanguage === 'uk') return text;
      const registerMatch = /^Регістр (\d+)$/.exec(text);
      if (registerMatch) return t('registerNumber', {number: registerMatch[1]});
      const statusMatch = /^Код робочого стану (\d+)$/.exec(text);
      if (statusMatch) return t('operatingStatusCode', {number: statusMatch[1]});
      return DATA_TRANSLATIONS[text]?.[currentLanguage] ?? text;
    }
    function r413BmsFormula(value) {
      if (!Number.isFinite(value)) return '';
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      const configuredValue = value / 0.85;
      return t('r413BmsFormula', {
        value: configuredValue.toLocaleString(locale, {
          minimumFractionDigits: Number.isInteger(configuredValue) ? 0 : 1,
          maximumFractionDigits: 1
        })
      });
    }
    let lastData = null;
    let chartDemoRunning = false;
    let chartDemoCancelRequested = false;
    let demoRegisterRows = null;
    let demoFlowCase = '';
    let demoGeneratorPower = 0;
    let demoPvVoltage = 0;
    let demoPvPower = 0;
    let currentView = 'dashboard';
    let lcdPageIndex = 0;
    const lcdInformationPageCount = 26;
    let lcdEnterNotice = false;
    let refreshInFlight = false;
    let refreshTimer = null;
    let refreshController = null;
    let lastLoggedSiteVisits = null;
    const requestIntervals = [500, 1000, 2000, 5000, 10000];
    const flowAnimationStates = new Map();
    let chartDefinitions = new Map();
    function savedSelections(name) {
      try {
        return new Set(JSON.parse(window.localStorage.getItem(name) || '[]'));
      } catch {
        return new Set();
      }
    }
    function saveSelections(name, selections) {
      try {
        window.localStorage.setItem(name, JSON.stringify([...selections]));
      } catch {
        // The dashboard still works when browser storage is unavailable.
      }
    }
    function savedMap(name) {
      try {
        const value = JSON.parse(window.localStorage.getItem(name) || '{}');
        return new Map(Object.entries(value && typeof value === 'object' ? value : {}));
      } catch {
        return new Map();
      }
    }
    function saveMap(name, values) {
      try {
        window.localStorage.setItem(name, JSON.stringify(Object.fromEntries(values)));
      } catch {
        // Gauge appearance remains stable for the current page when storage is unavailable.
      }
    }
    const chartSelections = savedSelections('inverter-chart-values-v2');
    const dashboardSelections = savedSelections('inverter-dashboard-gauges-v2');
    const chartHistory = new Map();
    const dashboardGaugeRanges = savedMap('inverter-dashboard-gauge-ranges-v2');
    const dashboardGaugeColours = savedMap('inverter-dashboard-gauge-colours-v2');
    const chartWindowSeconds = 120;
    const chartWindowMilliseconds = chartWindowSeconds * 1000;

    function numericValue(value) {
      const parsed = Number.parseFloat(value);
      return Number.isFinite(parsed) ? parsed : null;
    }

    function collectChartDefinitions(data) {
      const definitions = new Map();
      const registerCategories = new Map(
        data.registers.map(register => [register.register, String(register.group || '')])
      );
      data.meters.forEach(meter => {
        const value = meter.available !== false && Number.isFinite(meter.value) ? meter.value : null;
        const bmsFormula = meter.register === 413 ? r413BmsFormula(value) : '';
        definitions.set(`meter-${meter.register}`, {
          key: `meter-${meter.register}`,
          register: meter.register,
          label: localizeDataText(meter.label),
          detail: `${t('gaugeDetail', {
            unit: meter.unit || t('unitValue'),
            register: meter.register
          })}${bmsFormula ? ` · ${bmsFormula}` : ''}`,
          unit: meter.unit,
          value,
          minimum: meter.minimum,
          maximum: meter.maximum,
          available: meter.available ?? !String(meter.source || '').toLowerCase().includes('mbpoll'),
          category: registerCategories.get(meter.register) || '',
          source: bmsFormula ? `R413 · ${bmsFormula}` : localizeDataText(meter.source)
        });
      });
      data.registers.forEach(register => {
        const value = numericValue(register.display);
        if (value === null) return;
        const bmsFormula = register.register === 413 && register.available ? r413BmsFormula(value) : '';
        definitions.set(`register-${register.register}`, {
          key: `register-${register.register}`,
          register: register.register,
          label: localizeDataText(register.name),
          detail: `R${register.register} · ${localizeDataText(register.group)}${bmsFormula ? ` · ${bmsFormula}` : ''}`,
          unit: register.unit,
          scale: Number(register.scale) || 1,
          signed: Boolean(register.signed),
          value,
          minimum: null,
          maximum: null,
          available: register.available,
          category: String(register.group || ''),
          source: register.available
            ? `R${register.register}${bmsFormula ? ` · ${bmsFormula}` : ''}`
            : t('noData')
        });
      });
      return definitions;
    }

    function updateGaugeSelectionActions() {
      const allSelected = chartDefinitions.size > 0 && [...chartDefinitions.keys()].every(key =>
        dashboardSelections.has(key) && chartSelections.has(key)
      );
      const noSelection = dashboardSelections.size === 0 && chartSelections.size === 0;
      const selectAllDisabled = chartDefinitions.size === 0 || allSelected;
      document.querySelector('#select-all-gauges').disabled = selectAllDisabled;
      document.querySelector('#chart-select-all').disabled = selectAllDisabled;
      document.querySelector('#clear-all-gauges').disabled = noSelection;
      document.querySelector('#chart-clear-all').disabled = noSelection;
    }

    function renderChartValueList() {
      const host = document.querySelector('#chart-value-list');
      const query = document.querySelector('#chart-search').value.trim().toLowerCase();
      const items = [...chartDefinitions.values()].filter(item =>
        `${item.label} ${item.detail} ${item.unit}`.toLowerCase().includes(query)
      );
      host.innerHTML = items.map(item => `<div class="value-option">
        <div class="value-name">${item.label}<small>${item.detail}</small></div>
        <div class="value-targets">
          <label><input type="checkbox" data-value-key="${item.key}" ${chartSelections.has(item.key) && dashboardSelections.has(item.key) ? 'checked' : ''}> ${t('dashboardChart')}</label>
        </div>
      </div>`).join('');
      updateGaugeSelectionActions();
    }

    function renderGaugePickerList() {
      const host = document.querySelector('#gauge-picker-list');
      const query = document.querySelector('#gauge-picker-search').value.trim().toLowerCase();
      const items = [...chartDefinitions.values()].filter(item =>
        `${item.label} ${item.detail} ${item.unit}`.toLowerCase().includes(query)
      );
      host.innerHTML = items.map(item => `<label class="gauge-picker-option">
        <input type="checkbox" data-picker-value-key="${item.key}" ${dashboardSelections.has(item.key) ? 'checked' : ''}>
        <span class="gauge-picker-name">${item.label}<small>${item.detail}${item.unit ? ` · ${item.unit}` : ''}</small></span>
      </label>`).join('');
      updateGaugeSelectionActions();
    }

    function renderGaugeSelectionChanges() {
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
      renderGaugePickerList();
    }

    function selectAllGaugeSelections() {
      chartDefinitions.forEach((_item, key) => {
        if (!dashboardSelections.has(key) || !chartSelections.has(key)) chartHistory.set(key, []);
        dashboardSelections.add(key);
        chartSelections.add(key);
      });
      renderGaugeSelectionChanges();
    }

    function clearGaugeSelections() {
      dashboardSelections.clear();
      chartSelections.clear();
      chartHistory.clear();
      renderGaugeSelectionChanges();
    }

    function openGaugePicker() {
      const picker = document.querySelector('#gauge-picker');
      // Rebuild from the original server labels on every open so the dialog
      // can never retain labels produced for a previously selected language.
      if (lastData) chartDefinitions = collectChartDefinitions(lastData);
      renderGaugePickerList();
      if (typeof picker.showModal === 'function') picker.showModal();
      else picker.setAttribute('open', '');
      window.setTimeout(() => document.querySelector('#gauge-picker-search').focus(), 0);
    }

    function updateChartDefinitions(data) {
      const next = collectChartDefinitions(data);
      const definitionSignature = definitions => [...definitions.values()].map(item =>
        `${item.key}:${item.label}:${item.detail}:${item.unit}:${item.minimum}:${item.maximum}`
      ).join('|');
      const oldSignature = definitionSignature(chartDefinitions);
      const nextSignature = definitionSignature(next);
      chartDefinitions = next;
      if (oldSignature !== nextSignature) {
        renderChartValueList();
        renderGaugePickerList();
        renderChartCards();
      }
      if (!chartDemoRunning) renderDashboardValues();
    }

    function niceGaugeLimit(value) {
      const positive = Math.max(1, Math.abs(value));
      const magnitude = 10 ** Math.floor(Math.log10(positive));
      const normalized = positive / magnitude;
      const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
      return step * magnitude;
    }

    function dashboardGaugeBounds(item) {
      if (Number.isFinite(item.minimum) && Number.isFinite(item.maximum) && item.maximum > item.minimum) {
        return {minimum: item.minimum, maximum: item.maximum};
      }
      const matchingMeter = chartDefinitions.get(`meter-${item.register}`);
      if (matchingMeter && Number.isFinite(matchingMeter.minimum) && Number.isFinite(matchingMeter.maximum)) {
        return {minimum: matchingMeter.minimum, maximum: matchingMeter.maximum};
      }
      if (item.unit === '%') return {minimum: 0, maximum: 100};

      const value = Number.isFinite(item.value) ? item.value : 0;
      const previousRange = dashboardGaugeRanges.get(item.key);
      if (previousRange && value >= previousRange.minimum && value <= previousRange.maximum) return previousRange;

      const range = value < 0
        ? {minimum: -niceGaugeLimit(Math.abs(value) * 1.2), maximum: niceGaugeLimit(Math.abs(value) * 1.2)}
        : {minimum: 0, maximum: niceGaugeLimit(Math.max(100, value * 1.2))};
      dashboardGaugeRanges.set(item.key, range);
      saveMap('inverter-dashboard-gauge-ranges-v2', dashboardGaugeRanges);
      return range;
    }

    function diagramGaugeColour(item) {
      const text = `${item.category || ''} ${item.label || ''} ${item.detail || ''}`.toLocaleLowerCase();
      if (/(pv|solar|соняч|солнеч)/u.test(text)) return '#fbbf24';
      if (/(генератор|generator)/u.test(text)) return '#fb923c';
      if (/(батар|акумулятор|аккумулятор|battery|bms|заряд|charge|discharg)/u.test(text)) return '#34d399';
      if (/(мереж|сеть|grid|mains)/u.test(text)) return '#60a5fa';
      if (/(навантаж|нагруз|load|home|дім|дом)/u.test(text)) return '#a78bfa';
      if (/(інвертор|инвертор|inverter|вихід|выход|output|вентилят|fan)/u.test(text)) return '#22d3ee';
      return null;
    }

    function dashboardGaugeColour(item) {
      const diagramColour = diagramGaugeColour(item);
      if (diagramColour) return diagramColour;
      const key = item.key;
      const saved = dashboardGaugeColours.get(key);
      if (colours.includes(saved)) return saved;
      const activeColours = [...dashboardSelections]
        .filter(selectedKey => selectedKey !== key)
        .map(selectedKey => dashboardGaugeColours.get(selectedKey));
      const colour = colours.reduce((best, candidate) => {
        const uses = activeColours.filter(value => value === candidate).length;
        const bestUses = activeColours.filter(value => value === best).length;
        return uses < bestUses ? candidate : best;
      }, colours[0]);
      dashboardGaugeColours.set(key, colour);
      saveMap('inverter-dashboard-gauge-colours-v2', dashboardGaugeColours);
      return colour;
    }

    function dashboardGaugeItems() {
      return [...dashboardSelections]
        .filter(key => chartDefinitions.has(key))
        .map(key => {
          const item = chartDefinitions.get(key);
          return {...item, ...dashboardGaugeBounds(item), colour: dashboardGaugeColour(item)};
        });
    }

    function showsSpeedometer(item) {
      if (!Number.isFinite(item.value) || item.value === 0) return false;
      const category = String(item.category || '').toLocaleLowerCase();
      const label = String(item.label || '').toLocaleLowerCase();
      const settingsOrModes = /(налаштуван|настрой|setting|режим|mode)/u;
      const stateValue = !item.unit && /(стан|состояни|state|status)/u.test(label);
      return !settingsOrModes.test(category) && !settingsOrModes.test(label) && !stateValue;
    }

    function dashboardGaugeSignature(gauges) {
      return `${currentLanguage}|${gauges.map(gauge =>
        `${gauge.key}:${gauge.label}:${gauge.detail}:${gauge.unit}:${gauge.minimum}:${gauge.maximum}:${gauge.colour}:${showsSpeedometer(gauge)}`).join('|')}`;
    }

    function renderDashboardValues() {
      const gauges = dashboardGaugeItems();
      document.querySelector('#dashboard-gauge-toolbar').hidden = gauges.length === 0;
      if (!gauges.length) {
        const host = document.querySelector('#gauges');
        host.classList.add('empty-dashboard');
        host.innerHTML = addGaugeMarkup(true);
        host.dataset.keys = `${currentLanguage}|empty`;
        return;
      }
      renderGauges(gauges);
    }

    function renderChartCards() {
      const grid = document.querySelector('#chart-grid');
      const selected = [...chartSelections].filter(key => chartDefinitions.has(key));
      document.querySelector('#chart-demo-button').disabled = false;
      document.querySelector('#chart-selection-count').textContent =
        selected.length ? t('selectedSummary', {count: selected.length}) : t('noValuesSelected');

      if (!selected.length) {
        grid.innerHTML = `<div class="chart-empty">${t('selectValues')}</div>`;
        return;
      }

      grid.innerHTML = selected.map((key, index) => {
        const item = chartDefinitions.get(key);
        return `<article class="chart-card" style="--accent:${colours[index % colours.length]}">
          <div class="chart-card-head">
            <h3 title="${item.label}">${item.label}</h3>
            <div class="chart-latest" id="latest-${key}">—</div>
          </div>
          <div class="muted">${item.detail}</div>
          <canvas id="chart-${key}" data-chart-key="${key}" aria-label="${t('chartAria', {label: item.label})}"></canvas>
        </article>`;
      }).join('');
      requestAnimationFrame(drawAllCharts);
    }

    function recordChartSamples(data) {
      updateChartDefinitions(data);
      if (chartDemoRunning) {
        if (!document.querySelector('#charts-view').hidden) drawAllCharts();
        return;
      }
      const now = Date.now();
      chartSelections.forEach(key => {
        const item = chartDefinitions.get(key);
        if (!item || item.available === false || !Number.isFinite(item.value)) return;
        const history = chartHistory.get(key) || [];
        history.push({time: now, value: item.value});
        trimChartHistory(history, now);
        chartHistory.set(key, history);
      });
      if (!document.querySelector('#charts-view').hidden) drawAllCharts();
    }

    function interpolate(start, end, ratio) {
      return start + (end - start) * Math.max(0, Math.min(1, ratio));
    }

    function realisticDemoScenario(elapsedSeconds) {
      const second = elapsedSeconds % chartWindowSeconds;
      const ripple = Math.sin(second * .37);
      let gridAvailable = true;
      let pvVoltage;
      let pvPower;
      let loadPower;
      let batteryCurrent;
      let batterySoc;
      let statusCode;
      let outputPriority;
      let chargingPriority;
      let caseKey;
      let generatorPower = 0;

      if (second < 20) {
        // PV supplies the home and charges the battery; surplus production is curtailed.
        gridAvailable = false;
        pvVoltage = 326 + ripple * 4;
        pvPower = 7200 + Math.sin(second * .21) * 260;
        loadPower = 2500 + Math.sin(second * .29) * 140;
        batteryCurrent = 42 + ripple * 1.5;
        batterySoc = 72 + second * .08;
        statusCode = 4;
        outputPriority = 2;
        chargingPriority = 1;
        caseKey = 'demoSolarChargeExport';
      } else if (second < 40) {
        // Grid supplies the home and charges the battery.
        pvVoltage = 0;
        pvPower = 0;
        loadPower = 2900 + ripple * 130;
        batteryCurrent = 18 + ripple;
        batterySoc = 73.6 + (second - 20) * .05;
        statusCode = 3;
        outputPriority = 0;
        chargingPriority = 0;
        caseKey = 'demoGridHome';
      } else if (second < 60) {
        // With PV and AC input unavailable, the battery supplies the home.
        gridAvailable = false;
        pvVoltage = 0;
        pvPower = 0;
        loadPower = 2300 + Math.sin(second * .31) * 160;
        batteryCurrent = -loadPower / 51.8;
        batterySoc = 74.4 - (second - 40) * .09;
        statusCode = 5;
        outputPriority = 0;
        chargingPriority = 2;
        caseKey = 'demoBatteryHome';
      } else if (second < 80) {
        // Solar supplies the home; surplus production is curtailed and the battery remains idle.
        gridAvailable = false;
        pvVoltage = 324 + ripple * 3;
        pvPower = 5600 + ripple * 220;
        loadPower = 2700 + Math.sin(second * .27) * 130;
        batteryCurrent = ripple * .08;
        batterySoc = 72.6;
        statusCode = 4;
        outputPriority = 2;
        chargingPriority = 1;
        caseKey = 'demoSolarExport';
      } else if (second < 100) {
        // The generator is a one-way source that supplies the inverter and home.
        gridAvailable = false;
        pvVoltage = 0;
        pvPower = 0;
        loadPower = 2800 + Math.sin(second * .25) * 120;
        batteryCurrent = 0;
        batterySoc = 72.5;
        statusCode = 6;
        outputPriority = 3;
        chargingPriority = 0;
        generatorPower = 3400 + ripple * 180;
        caseKey = 'demoGeneratorHome';
      } else {
        // With AC input unavailable, solar and battery jointly supply the home.
        gridAvailable = false;
        pvVoltage = 320 + ripple * 3;
        pvPower = 1500 + ripple * 120;
        loadPower = 2500 + Math.sin(second * .25) * 120;
        batteryCurrent = -(20 + ripple);
        batterySoc = 72.5 - (second - 100) * .07;
        statusCode = 4;
        outputPriority = 2;
        chargingPriority = 1;
        caseKey = 'demoMixedSources';
      }

      const gridVoltage = gridAvailable ? 230 + Math.sin(second * .19) * 1.4 : 0;
      const gridFrequency = gridAvailable ? 50 + Math.sin(second * .17) * .025 : 0;
      const batteryVoltage = 52.1 + (batterySoc - 75) * .09 + batteryCurrent * .018;
      const batteryTemperature = 29.5 + Math.abs(batteryCurrent) * .055 + Math.sin(second * .08) * .3;
      const batteryPower = batteryVoltage * batteryCurrent;
      const powerFactor = .86;
      const apparentLoadPower = loadPower / powerFactor;
      const gridPower = Math.max(0,
        loadPower + Math.max(0, batteryPower) - Math.max(0, pvPower) - Math.max(0, -batteryPower)
      );
      const inputMode = generatorPower > 20 ? 2 : 0;
      const generatorVoltage = generatorPower > 20 ? 230 : 0;
      const generatorCurrent = generatorVoltage > 0 ? generatorPower / generatorVoltage : 0;
      const pvChargingCurrent = pvPower > loadPower ? Math.max(0, batteryCurrent) : 0;
      const energyProgress = second / chartWindowSeconds;
      return {
        statusCode,
        caseKey,
        generatorPower,
        pvVoltage,
        pvPower,
        values: new Map([
          [70, 0], [71, 0], [72, 0], [73, 0], [74, 0],
          [75, 65535], [76, 65535], [77, 1], [78, 8224], [79, 65535], [80, 1],
          [81, gridVoltage], [82, gridVoltage > 0 ? gridPower / gridVoltage : 0],
          [83, gridFrequency], [84, gridPower],
          [85, generatorVoltage], [86, generatorCurrent], [87, generatorVoltage > 0 ? 50 : 0],
          [88, generatorPower],
          [89, 230 + Math.sin(second * .13) * .8], [90, loadPower / 230], [91, 50],
          [92, loadPower], [93, apparentLoadPower], [94, loadPower / 120], [95, gridPower],
          [129, batteryVoltage], [130, batteryCurrent],
          [133, batterySoc], [134, batteryPower],
          [137, batteryVoltage], [138, batteryCurrent], [139, batterySoc],
          [140, batteryTemperature + .6], [141, 57.1],
          [144, 1], [151, pvVoltage], [152, pvVoltage > 0 ? pvPower / pvVoltage : 0],
          [153, pvPower], [154, 0], [155, 0], [156, 0],
          [157, 8.4 + energyProgress], [158, 1820.7 + energyProgress],
          [159, pvChargingCurrent], [160, 0], [161, pvPower],
          [162, 428.6 + energyProgress], [163, 3420.4 + energyProgress],
          [164, 4.2 + energyProgress], [165, 96.3 + energyProgress],
          [166, 812.5 + energyProgress], [167, 6432.8 + energyProgress],
          [168, 3.1 + energyProgress], [169, 71.8 + energyProgress],
          [170, 605.7 + energyProgress], [171, 4890.4 + energyProgress],
          [172, 7.8 + energyProgress], [173, 181.6 + energyProgress],
          [174, 1530.2 + energyProgress], [175, 12270.5 + energyProgress],
          [176, 6.9 + energyProgress], [177, 162.4 + energyProgress],
          [178, 1378.1 + energyProgress], [179, 11042.7 + energyProgress],
          [180, 1.2 + energyProgress], [181, 28.5 + energyProgress],
          [182, 241.8 + energyProgress], [183, 1920.6 + energyProgress],
          [184, 2.8 + energyProgress], [185, 65.7 + energyProgress],
          [186, 558.4 + energyProgress], [187, 4471.2 + energyProgress],
          [188, loadPower], [189, 0], [190, 0],
          [321, inputMode], [323, outputPriority], [324, chargingPriority], [325, statusCode],
          [337, 2], [339, batterySoc],
          [341, 47.5], [342, batteryVoltage],
          [343, Math.max(0, -batteryCurrent)], [344, Math.max(0, batteryCurrent)],
          [345, 61], [346, 48], [349, 48], [350, 2],
          [376, 57.1], [377, 54.4], [378, 80], [379, 80], [383, 58.4],
          [385, 2], [386, 30],
          [401, 1], [402, 1], [403, 8306],
          [404, batteryVoltage], [405, batteryCurrent],
          [406, batteryTemperature + .6], [407, batterySoc], [408, 100],
          [409, 128], [410, 170], [411, 57.1], [412, 80], [413, 120],
          [414, 20], [415, 10], [416, 48], [417, 57.6],
          [529, outputPriority], [530, inputMode],
          [537, 230], [538, 50], [539, loadPower / 230], [541, loadPower],
          [542, apparentLoadPower], [545, loadPower / 120], [818, 46.2], [823, 31.5 + pvPower / 10000],
          [16643, outputPriority], [16644, inputMode], [16645, chargingPriority],
          [16655, 170]
        ])
      };
    }

    function demoSolarEnergySummary(elapsedSeconds) {
      // The 120-second demo represents a compressed 12-hour operating window.
      const boundedSeconds = Math.max(0, Math.min(chartWindowSeconds, elapsedSeconds));
      const simulatedSecondsPerDemoSecond = 360;
      const integrationStep = .25;
      let generatedKwh = 0;
      for (let second = 0; second < boundedSeconds; second += integrationStep) {
        const step = Math.min(integrationStep, boundedSeconds - second);
        const pvPower = realisticDemoScenario(second + step / 2).pvPower;
        generatedKwh += Math.max(0, Number(pvPower) || 0)
          * step * simulatedSecondsPerDemoSecond / 3_600_000;
      }
      return {
        today_kwh: generatedKwh,
        week_kwh: 93.8 + generatedKwh,
        month_kwh: 428.6 + generatedKwh,
        year_kwh: 3420.4 + generatedKwh,
        error: ''
      };
    }

    function demoRawValue(register, value) {
      const scale = Number(register.scale) || 1;
      let raw = Math.round(value / scale);
      if (register.signed && raw < 0) raw += 65536;
      return Math.max(0, Math.min(65534, raw));
    }

    function demoDisplayValue(value, scale) {
      if (scale === .01) return value.toFixed(2);
      if (scale === .1) return value.toFixed(1);
      if (scale === 1) return Math.round(value).toString();
      return Number(value.toFixed(3)).toString();
    }

    function demoStatusText(statusCode) {
      return ({
        1: 'Ймовірно робота від мережі або байпас',
        2: 'Ймовірно робота інвертора від батареї або PV',
        3: 'Ймовірно заряджання або активна робота'
      })[statusCode] || 'Очікування або невідомий стан';
    }

    function applyDemoEnergyFrame(scenario) {
      demoFlowCase = scenario.caseKey;
      demoGeneratorPower = scenario.generatorPower;
      demoPvVoltage = scenario.pvVoltage;
      demoPvPower = scenario.pvPower;
      demoRegisterRows = lastData ? lastData.registers.map(register => {
        const value = scenario.values.get(register.register);
        if (!Number.isFinite(value)) return register;
        const display = register.register === 157
          ? demoStatusText(scenario.statusCode)
          : demoDisplayValue(value, Number(register.scale) || 1);
        return {
          ...register,
          display,
          raw: demoRawValue(register, value),
          available: true
        };
      }) : [];
      if (lastData) {
        renderEnergyFlow(lastData, demoRegisterRows);
        renderLcd(lastData, demoRegisterRows);
      }
    }

    function trimChartHistory(history, currentTime) {
      const oldestAllowed = currentTime - chartWindowMilliseconds;
      while (history.length && history[0].time < oldestAllowed) history.shift();
    }

    function formatChartTime(timestamp) {
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      return new Date(timestamp).toLocaleTimeString(locale, {
        timeZone: 'Europe/Madrid',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }

    async function fillChartExampleData() {
      if (chartDemoRunning) {
        chartDemoCancelRequested = true;
        return;
      }

      const selected = [...chartSelections].filter(key => chartDefinitions.has(key));
      const registerKeys = [...chartDefinitions.keys()].filter(key => key.startsWith('register-'));
      const meterKeys = [...chartDefinitions.keys()].filter(key => key.startsWith('meter-'));
      const demoKeys = [...new Set([...registerKeys, ...meterKeys, ...selected])];
      if (!demoKeys.length) return;

      const buttons = document.querySelectorAll('.all-data-demo-button');
      const setButtonState = (text, disabled = false) => buttons.forEach(button => {
        button.textContent = text;
        button.disabled = disabled;
      });
      chartDemoRunning = true;
      chartDemoCancelRequested = false;
      document.documentElement.classList.add('demo-energy-flow');
      demoKeys.forEach(key => chartHistory.set(key, []));
      applyDemoEnergyFrame(realisticDemoScenario(0));
      if (lastData) render(lastData);
      drawAllCharts();

      try {
        const demoStartedAt = Date.now();
        while (Date.now() - demoStartedAt < chartWindowMilliseconds) {
          const elapsedBeforeWait = Math.floor((Date.now() - demoStartedAt) / 1000);
          setButtonState(t('stopDemo', {
            elapsed: elapsedBeforeWait,
            seconds: chartWindowSeconds,
            count: registerKeys.length
          }));
          const selectedIndex = Number(document.querySelector('#poll-rate').value);
          await wait(requestIntervals[selectedIndex] ?? 2000);
          if (chartDemoCancelRequested) break;

          const now = Date.now();
          const elapsedSeconds = Math.min(
            chartWindowSeconds - .001,
            (now - demoStartedAt) / 1000
          );
          const scenario = realisticDemoScenario(elapsedSeconds);
          applyDemoEnergyFrame(scenario);
          registerKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const history = chartHistory.get(key) || [];
            const scenarioValue = scenario.values.get(item.register);
            if (Number.isFinite(scenarioValue)) item.value = scenarioValue;
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          meterKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const registerKey = key.replace('meter-', 'register-');
            const registerItem = chartDefinitions.get(registerKey);
            const scenarioValue = scenario.values.get(item.register);
            if (Number.isFinite(scenarioValue)) item.value = scenarioValue;
            else if (registerItem) item.value = registerItem.value;
            if (registerItem) registerItem.value = item.value;
            const history = chartHistory.get(key) || [];
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          const elapsed = Math.min(
            chartWindowSeconds,
            Math.floor((now - demoStartedAt) / 1000)
          );
          setButtonState(t('stopDemo', {
            elapsed,
            seconds: chartWindowSeconds,
            count: registerKeys.length
          }));
          renderDashboardValues();
          renderRegisters(demoRegisterRows);
          renderSolarEnergy(demoSolarEnergySummary(elapsedSeconds));
          if (lastData) {
            renderEnergyFlow(lastData, demoRegisterRows);
            renderLcd(lastData, demoRegisterRows);
          }
          drawAllCharts();
        }
      } finally {
        chartDemoRunning = false;
        chartDemoCancelRequested = false;
        document.documentElement.classList.remove('demo-energy-flow');
        demoRegisterRows = null;
        demoFlowCase = '';
        demoGeneratorPower = 0;
        demoPvVoltage = 0;
        demoPvPower = 0;
        setButtonState(t('runDemo'));
        if (lastData) {
          recordChartSamples(lastData);
          render(lastData);
        }
      }
    }

    function drawChart(canvas, item, history, colour) {
      const width = Math.max(1, canvas.clientWidth);
      const height = canvas.clientHeight || 220;
      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = Math.round(width * pixelRatio);
      canvas.height = Math.round(height * pixelRatio);
      const context = canvas.getContext('2d');
      context.scale(pixelRatio, pixelRatio);
      context.clearRect(0, 0, width, height);
      const themeStyles = window.getComputedStyle(document.documentElement);
      const mutedColour = themeStyles.getPropertyValue('--muted').trim();
      const gridColour = themeStyles.getPropertyValue('--chart-grid-line').trim();

      const compactChart = width < 420;
      const padding = {
        left: compactChart ? 42 : 48,
        right: compactChart ? 8 : 14,
        top: 16,
        bottom: 28
      };
      const plotWidth = width - padding.left - padding.right;
      const plotHeight = height - padding.top - padding.bottom;
      const values = history.map(point => point.value);
      let minimum = values.length ? Math.min(...values) : 0;
      let maximum = values.length ? Math.max(...values) : 1;
      if (minimum === maximum) {
        const margin = Math.abs(minimum) * .08 || 1;
        minimum -= margin;
        maximum += margin;
      } else {
        const margin = (maximum - minimum) * .1;
        minimum -= margin;
        maximum += margin;
      }

      context.font = '10px system-ui';
      context.fillStyle = mutedColour;
      context.strokeStyle = gridColour;
      context.lineWidth = 1;
      for (let line = 0; line <= 4; line += 1) {
        const ratio = line / 4;
        const y = padding.top + plotHeight * ratio;
        context.beginPath();
        context.moveTo(padding.left, y);
        context.lineTo(width - padding.right, y);
        context.stroke();
        const label = maximum - (maximum - minimum) * ratio;
        context.fillText(Number(label.toFixed(2)).toString(), 3, y + 3);
      }

      const endTime = history.length ? history.at(-1).time : Date.now();
      const startTime = endTime - chartWindowMilliseconds;
      const timeTickCount = width < 340 ? 2 : 3;
      for (let tick = 0; tick <= timeTickCount; tick += 1) {
        const ratio = tick / timeTickCount;
        const x = padding.left + plotWidth * ratio;
        context.beginPath();
        context.moveTo(x, padding.top);
        context.lineTo(x, padding.top + plotHeight);
        context.stroke();
        context.fillStyle = mutedColour;
        context.textAlign = tick === 0 ? 'left' : tick === timeTickCount ? 'right' : 'center';
        context.fillText(
          formatChartTime(startTime + (endTime - startTime) * ratio),
          x,
          height - 7
        );
      }

      if (history.length) {
        context.strokeStyle = colour;
        context.lineWidth = 2.5;
        context.lineJoin = 'round';
        context.lineCap = 'round';
        context.beginPath();
        history.forEach((point, index) => {
          const timeRatio = Math.max(
            0,
            Math.min(1, (point.time - startTime) / chartWindowMilliseconds)
          );
          const x = padding.left + plotWidth * timeRatio;
          const y = padding.top + plotHeight * (maximum - point.value) / (maximum - minimum);
          if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
        });
        context.stroke();
      }

      const latest = document.querySelector(`#latest-${item.key}`);
      if (latest) latest.textContent = history.length
        ? `${Number(history.at(-1).value.toFixed(2))} ${item.unit}`.trim()
        : t('waiting');
    }

    function drawAllCharts() {
      document.querySelectorAll('canvas[data-chart-key]').forEach((canvas, index) => {
        const key = canvas.dataset.chartKey;
        const item = chartDefinitions.get(key);
        if (item) drawChart(canvas, item, chartHistory.get(key) || [], colours[index % colours.length]);
      });
    }

    function scaleNumber(value, range) {
      if (Math.abs(value) >= 1000) {
        const compact = value / 1000;
        return `${Number(compact.toFixed(compact % 1 ? 1 : 0))}k`;
      }
      const decimals = range <= 20 ? 1 : 0;
      return Number(value.toFixed(decimals)).toString();
    }

    function scaleMarkup(meter) {
      const centreX = 120;
      const centreY = 120;
      const range = meter.maximum - meter.minimum;
      let markup = '';

      for (let index = 0; index <= 20; index += 1) {
        const angle = Math.PI + (Math.PI * index / 20);
        const major = index % 5 === 0;
        const outerRadius = 106;
        const innerRadius = major ? 94 : 99;
        const x1 = centreX + Math.cos(angle) * innerRadius;
        const y1 = centreY + Math.sin(angle) * innerRadius;
        const x2 = centreX + Math.cos(angle) * outerRadius;
        const y2 = centreY + Math.sin(angle) * outerRadius;
        markup += `<line class="tick${major ? ' major' : ''}" x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}"/>`;

        if (major) {
          const labelRadius = 81;
          const labelX = centreX + Math.cos(angle) * labelRadius;
          const labelY = centreY + Math.sin(angle) * labelRadius;
          const value = meter.minimum + range * index / 20;
          markup += `<text class="scale-label" x="${labelX.toFixed(2)}" y="${labelY.toFixed(2)}">${scaleNumber(value, range)}</text>`;
        }
      }
      return markup;
    }

    function addGaugeMarkup(empty = false) {
      return `<button class="add-gauge-card" type="button" data-open-gauge-picker aria-label="${t('addGauge')}">
        <span class="add-gauge-plus">+</span>
        <span class="add-gauge-label">${empty ? t('emptyDashboard') : t('addGauge')}</span>
      </button>`;
    }

    function gaugeMarkup(meter) {
      const label = localizeDataText(meter.label);
      const showSpeedometer = showsSpeedometer(meter);
      return `<article class="gauge-card${showSpeedometer ? '' : ' no-speedometer'}" draggable="true" data-dashboard-key="${meter.key}" style="--accent:${meter.colour}">
        <div class="gauge-actions">
          <button class="drag-handle" type="button" draggable="false" title="${t('dragGauge')}" aria-label="${t('dragGauge')}">⠿</button>
          <button class="remove-value" type="button" draggable="false" data-remove-dashboard="${meter.key}" title="${t('removeDashboard')}" aria-label="${t('removeDashboard')}">×</button>
        </div>
        <div class="gauge-heading">
          <div class="gauge-title">${label}</div>
          <span class="gauge-number">R${meter.register}</span>
        </div>
        ${showSpeedometer ? `<svg viewBox="0 0 240 145" role="img" aria-label="${label}">
          <path class="track" d="M20 120 A100 100 0 0 1 220 120"/>
          <path class="progress" d="M20 120 A100 100 0 0 1 220 120"/>
          ${scaleMarkup(meter)}
          <line class="needle" x1="120" y1="120" x2="120" y2="33"/>
          <circle class="hub" cx="120" cy="120" r="7"/>
        </svg>` : ''}
        <div class="reading"><span class="value">—</span><span class="unit">${meter.unit}</span></div>
        <div class="source">${meter.detail}</div>
      </article>`;
    }

    function renderGauges(meters) {
      const host = document.querySelector('#gauges');
      host.classList.remove('empty-dashboard');
      const signature = dashboardGaugeSignature(meters);
      if (host.dataset.keys !== signature) {
        host.dataset.keys = signature;
        host.innerHTML = meters.map(gaugeMarkup).join('') + addGaugeMarkup();
      }
      meters.forEach(meter => {
        const card = host.querySelector(`[data-dashboard-key="${meter.key}"]`);
        if (!card) return;
        const hasValue = Number.isFinite(meter.value);
        const value = hasValue ? meter.value : 0;
        const ratio = hasValue ? Math.max(0, Math.min(1, (value - meter.minimum) / (meter.maximum - meter.minimum))) : 0;
        const needleTransform = `rotate(${-90 + ratio * 180}deg)`;
        const progressOffset = `${283 * (1 - ratio)}`;
        const valueText = hasValue ? Number(value.toFixed(2)).toString() : '—';
        const needle = card.querySelector('.needle');
        const progress = card.querySelector('.progress');
        const valueElement = card.querySelector('.value');
        const sourceElement = card.querySelector('.source');

        if (needle && needle.style.transform !== needleTransform) needle.style.transform = needleTransform;
        if (progress && progress.style.strokeDashoffset !== progressOffset) progress.style.strokeDashoffset = progressOffset;
        if (valueElement.textContent !== valueText) valueElement.textContent = valueText;
        const localizedSource = meter.available === false ? t('noData') : localizeDataText(meter.source || meter.detail);
        if (sourceElement.textContent !== localizedSource) sourceElement.textContent = localizedSource;

      });
    }

    function renderRegisters(registers) {
      const query = document.querySelector('#search').value.trim().toLowerCase();
      const shown = registers.filter(item =>
        `${item.register} ${localizeDataText(item.group)} ${localizeDataText(item.name)} ${localizeDataText(item.display)} ${item.unit}`.toLowerCase().includes(query)
      );
      const available = registers.filter(item => item.available).length;
      document.querySelector('#register-count').textContent =
        t('registerCount', {
          available,
          waiting: registers.length - available,
          shown: shown.length
        });
      document.querySelector('#registers').innerHTML = shown.map(item => {
        const value = numericValue(item.display);
        const bmsFormula = item.register === 413 && item.available ? r413BmsFormula(value) : '';
        return `<tr class="${item.available ? '' : 'unavailable'}">
          <td>R${item.register}</td><td>${localizeDataText(item.group)}</td><td>${localizeDataText(item.name)}</td>
          <td>${localizeDataText(item.display)} ${item.unit}${bmsFormula ? `<br><small>${bmsFormula}</small>` : ''}</td><td>${item.raw ?? '—'}</td></tr>`;
      }).join('');
    }

    function formatFileSize(bytes) {
      const value = Number(bytes || 0);
      if (value < 1024) return `${value} B`;
      if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
      if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
      return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }

    function renderRegisterLog(log = {}) {
      const status = document.querySelector('#register-log-status');
      const active = Boolean(log.active);
      status.classList.toggle('active', active && !log.error);
      status.classList.toggle('error-text', Boolean(log.error));
      if (log.error) {
        status.textContent = t('registerLogError', {error: localizeDataText(log.error)});
      } else if (active) {
        status.textContent = t('registerLogActive', {
          filename: log.filename,
          changes: log.changes || 0,
          size: formatFileSize(log.size_bytes)
        });
      } else if (log.available) {
        status.textContent = t('registerLogStopped', {
          filename: log.filename,
          changes: log.changes || 0,
          size: formatFileSize(log.size_bytes)
        });
      } else {
        status.textContent = t('registerLogIdle');
      }
      if (Number.isFinite(Number(log.free_bytes))) {
        status.textContent += ` · ${t('registerLogStorage', {
          free: formatFileSize(log.free_bytes),
          count: log.pruned_files || 0
        })}`;
      }
      if (active && log.physical_button_capture) {
        status.textContent += ` · ${t('registerLogPhysicalCapture', {
          seconds: Number(log.capture_interval_seconds || .5).toLocaleString(
            currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB'
          )
        })}`;
      }
      document.querySelector('#register-log-start').disabled = active;
      document.querySelector('#register-log-stop').disabled = !active;
      document.querySelector('#register-log-note').disabled = !active;
      document.querySelector('#register-log-mark').disabled = !active;
      document.querySelector('#register-log-download').hidden = !log.available;
      document.querySelector('#poll-rate').disabled = active;
      document.querySelector('#read-mode').disabled = active;
    }

    async function updateRegisterLog(action, note = '') {
      const buttons = document.querySelectorAll('#register-log-start, #register-log-stop, #register-log-mark');
      buttons.forEach(button => button.disabled = true);
      try {
        const payload = {action, note, language: currentLanguage};
        if (action === 'start') {
          payload.translations = Object.fromEntries(
            Object.entries(DATA_TRANSLATIONS).map(([source, translations]) => [
              source,
              currentLanguage === 'uk' ? source : translations[currentLanguage] ?? source
            ])
          );
        }
        const response = await fetch('/api/register-log', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        if (lastData) lastData.register_log = result;
        if (action === 'mark') document.querySelector('#register-log-note').value = '';
        renderRegisterLog(result);
      } catch (error) {
        const status = document.querySelector('#register-log-status');
        status.className = 'logger-status error-text';
        status.textContent = t('registerLogRequestError', {error: localizeDataText(error.message)});
        const active = Boolean(lastData?.register_log?.active);
        document.querySelector('#register-log-start').disabled = active;
        document.querySelector('#register-log-stop').disabled = !active;
        document.querySelector('#register-log-mark').disabled = !active;
      }
    }

    function formatSolarEnergy(kilowattHours) {
      if (kilowattHours === null || kilowattHours === undefined || kilowattHours === '') return t('noData');
      const value = Number(kilowattHours);
      if (!Number.isFinite(value)) return t('noData');
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      if (value < 1) return `${Math.round(value * 1000).toLocaleString(locale)} Wh`;
      if (value < 1000) return `${value.toLocaleString(locale, {maximumFractionDigits: 2})} kWh`;
      return `${(value / 1000).toLocaleString(locale, {maximumFractionDigits: 2})} MWh`;
    }

    function renderSolarEnergy(summary = {}) {
      const values = {
        '#solar-energy-today': summary.today_kwh,
        '#solar-energy-week': summary.week_kwh,
        '#solar-energy-month': summary.month_kwh,
        '#solar-energy-year': summary.year_kwh
      };
      Object.entries(values).forEach(([selector, value]) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = formatSolarEnergy(value);
      });
      const error = document.querySelector('#solar-energy-error');
      if (error) {
        error.textContent = summary.error ? localizeDataText(summary.error) : '';
        error.hidden = !summary.error;
      }
    }

    function renderEnergyFlow(data, registers = data.registers || []) {
      const byNumber = new Map(registers.map(register => [register.register, register]));
      const firstRegister = numbers => numbers
        .map(number => byNumber.get(number))
        .find(register => register?.available);
      const numberValue = numbers => {
        const register = firstRegister(numbers);
        return register ? numericValue(register.display) : null;
      };
      const summedValue = numbers => {
        const values = numbers
          .map(number => byNumber.get(number))
          .filter(register => register?.available)
          .map(register => numericValue(register.display))
          .filter(Number.isFinite);
        return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
      };
      const registerText = (sources, fallbackNumbers = []) => {
        const actualNumbers = sources
          .flat()
          .map(source => typeof source === 'number' ? source : source?.register)
          .filter(Number.isFinite);
        const numbers = actualNumbers.length ? actualNumbers : fallbackNumbers;
        return [...new Set(numbers)].map(number => `R${number}`).join(' · ') || '—';
      };
      const reading = (value, unit, digits = 0) =>
        Number.isFinite(value) ? `${Number(value.toFixed(digits))} ${unit}` : t('noData');
      const modeDetails = (source, modes) => {
        const raw = Number(source?.raw);
        if (!source?.available || !Number.isFinite(raw) || raw === 65535) {
          return {label: '—', description: ''};
        }
        return modes[raw] || {label: `#${raw}`, description: ''};
      };
      const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element && element.textContent !== value) element.textContent = value;
      };
      const setModeText = (selector, definitionSelector, mode) => {
        const description = mode.description ? t(mode.description) : '';
        setText(selector, mode.label);
        setText(definitionSelector, description);
        const element = document.querySelector(selector);
        if (element) element.title = description;
      };
      const setNode = (selector, enabled) =>
        document.querySelector(selector)?.classList.toggle('active', Boolean(enabled));
      const setFlow = (selector, enabled, reverse, watts) => {
        const connector = document.querySelector(selector);
        if (!connector) return;
        const now = performance.now();
        const previous = flowAnimationStates.get(selector) || {
          active: false,
          reverse: false,
          lastConfirmedAt: 0
        };
        const confirmedActive = Boolean(enabled);
        const selectedRate = Number(document.querySelector('#poll-rate')?.value);
        const holdMilliseconds = Math.max(750, (requestIntervals[selectedRate] ?? 2000) * 1.25);
        const temporarilyMissing = !confirmedActive && !Number.isFinite(watts);
        const active = confirmedActive || (
          temporarilyMissing
          && previous.active
          && now - previous.lastConfirmedAt <= holdMilliseconds
        );
        const directionReversed = confirmedActive ? Boolean(reverse) : previous.reverse;

        // Set the speed only when a flow starts. Updating animation-duration on
        // every Modbus cycle restarts the CSS animation and causes visible flicker.
        if (active && !previous.active) {
          const strength = Number.isFinite(watts) ? Math.abs(watts) : 0;
          const duration = Math.max(.55, Math.min(2.2, 2.2 - strength / 5000 * 1.5));
          connector.style.setProperty('--flow-duration', `${duration.toFixed(2)}s`);
        }
        if (connector.classList.contains('active') !== active) {
          connector.classList.toggle('active', active);
        }
        if (connector.classList.contains('reverse') !== directionReversed) {
          connector.classList.toggle('reverse', directionReversed);
        }
        flowAnimationStates.set(selector, {
          active,
          reverse: directionReversed,
          lastConfirmedAt: confirmedActive ? now : previous.lastConfirmedAt
        });
      };

      const gridVoltageSource = firstRegister([89]);
      const gridCurrentSource = firstRegister([82, 434]);
      const gridPowerSource = firstRegister([84, 437, 436]);
      const gridModeSource = firstRegister([325, 67]);
      const pvVoltageSource = firstRegister([151, 154]);
      const pvPowerSource = firstRegister([153, 156]);
      const loadPowerSource = firstRegister([92]);
      const inverterLoadSource = firstRegister([94]);
      const inverterFanSpeedSource = firstRegister([801]);
      const outputVoltageSource = firstRegister([537]);
      const outputCurrentSource = firstRegister([90]);
      const batteryVoltageSource = firstRegister([129, 137, 404, 342]);
      const batteryCurrentSource = firstRegister([130]);
      const batterySocSource = firstRegister([339]);
      const batteryPowerSource = firstRegister([134]);
      const inverterPrioritySource = firstRegister([529, 323, 16643]);
      const inverterAcModeSource = firstRegister([530, 321, 16644]);
      const inverterChargeModeSource = firstRegister([324, 16645]);
      const inverterStateSource = firstRegister([325, 67]);
      const gridVoltage = gridVoltageSource ? numericValue(gridVoltageSource.display) : null;
      const measuredGridCurrent = gridCurrentSource ? numericValue(gridCurrentSource.display) : null;
      const measuredGridPower = gridPowerSource ? numericValue(gridPowerSource.display) : null;
      const pvVoltage = chartDemoRunning && Number.isFinite(demoPvVoltage)
        ? demoPvVoltage
        : numberValue([151, 154]);
      const pvPower = chartDemoRunning && Number.isFinite(demoPvPower)
        ? demoPvPower
        : summedValue([153, 156]);
      const measuredPvCurrent = summedValue([152, 155]);
      const pvCurrent = Number.isFinite(measuredPvCurrent)
        ? Math.abs(measuredPvCurrent)
        : Number.isFinite(pvVoltage) && Math.abs(pvVoltage) > .1 && Number.isFinite(pvPower)
          ? Math.abs(pvPower / pvVoltage)
          : null;
      const loadPowerReading = loadPowerSource ? numericValue(loadPowerSource.display) : null;
      const measuredLoadPower = Number.isFinite(loadPowerReading) ? loadPowerReading : null;
      const inverterLoad = inverterLoadSource ? numericValue(inverterLoadSource.display) : null;
      const inverterFanSpeed = inverterFanSpeedSource ? numericValue(inverterFanSpeedSource.display) : null;
      const outputVoltage = outputVoltageSource ? numericValue(outputVoltageSource.display) : null;
      const outputCurrent = outputCurrentSource ? numericValue(outputCurrentSource.display) : null;
      const batteryVoltage = batteryVoltageSource ? numericValue(batteryVoltageSource.display) : null;
      const batteryCurrentReading = batteryCurrentSource ? numericValue(batteryCurrentSource.display) : null;
      const batteryCurrent = Number.isFinite(batteryCurrentReading) ? batteryCurrentReading : null;
      const batterySoc = batterySocSource ? numericValue(batterySocSource.display) : null;
      const batteryPowerReading = batteryPowerSource ? numericValue(batteryPowerSource.display) : null;
      const calculatedBatteryPower = Number.isFinite(batteryVoltage) && Number.isFinite(batteryCurrent)
        ? batteryVoltage * batteryCurrent
        : null;
      // R130 defines direction: positive charge, negative discharge. R134 supplies
      // the preferred magnitude so both battery values always use the same sign.
      const batteryPower = Number.isFinite(batteryPowerReading)
        ? Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
          ? Math.sign(batteryCurrent) * Math.abs(batteryPowerReading)
          : batteryPowerReading
        : calculatedBatteryPower;
      const batteryActive = (Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3)
        || (Number.isFinite(batteryPower) && Math.abs(batteryPower) > 20);
      const batteryCharging = batteryActive && (Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
        ? batteryCurrent > 0
        : batteryPower > 0);
      const batteryDischarging = batteryActive && (Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
        ? batteryCurrent < 0
        : batteryPower < 0);
      const pvActive = Number.isFinite(pvPower) && pvPower > 20;
      const solarDataVisible = pvActive;
      const pvReceiving = false;
      const gridVoltagePresent = Number.isFinite(gridVoltage) && Math.abs(gridVoltage) > .5;
      // R81 is physical mains input. R89 is inverter/load output and remains
      // available while the house is powered from PV or battery.
      const gridAvailable = gridVoltagePresent;
      const loadPower = Number.isFinite(measuredLoadPower) ? Math.max(0, measuredLoadPower) : null;
      const batteryChargePower = batteryCharging && Number.isFinite(batteryPower) ? Math.abs(batteryPower) : 0;
      const batteryDischargePower = batteryDischarging && Number.isFinite(batteryPower) ? Math.abs(batteryPower) : 0;
      const calculatedGridPower = chartDemoRunning
        ? gridAvailable && Number.isFinite(pvPower) && Number.isFinite(loadPower)
          ? loadPower + batteryChargePower - pvPower - batteryDischargePower
          : gridAvailable ? null : 0
        : gridAvailable && batteryCharging && Number.isFinite(loadPower)
          ? loadPower + batteryChargePower
        : gridAvailable && Number.isFinite(measuredGridPower)
          ? Math.abs(measuredGridPower)
          : gridAvailable && Number.isFinite(loadPower)
            ? Math.max(0, loadPower + batteryChargePower - Math.max(0, pvPower || 0))
            : null;
      // Grid is a one-way source. Surplus energy is never represented as grid export.
      const gridPower = Number.isFinite(calculatedGridPower) ? Math.max(0, calculatedGridPower) : null;
      const gridCurrent = gridAvailable && Number.isFinite(measuredGridCurrent)
        ? Math.abs(measuredGridCurrent)
        : Number.isFinite(gridPower) && Number.isFinite(gridVoltage) && Math.abs(gridVoltage) > .1
          ? Math.abs(gridPower / gridVoltage)
          : null;
      const generatorPower = chartDemoRunning && Number.isFinite(demoGeneratorPower)
        ? demoGeneratorPower
        : null;
      const generatorActive = Number.isFinite(generatorPower) && generatorPower > 20;
      const generatorVoltage = generatorActive ? 230 : null;
      const generatorCurrent = generatorActive && Number.isFinite(generatorVoltage)
        ? generatorPower / generatorVoltage
        : null;
      const batteryPowerSources = batteryPowerSource
        ? [batteryPowerSource]
        : [batteryVoltageSource, batteryCurrentSource];
      const gridRegisterSources = gridAvailable && batteryCharging && Number.isFinite(loadPower)
        ? [loadPowerSource, batteryPowerSources, gridVoltageSource, gridModeSource]
        : Number.isFinite(gridPower)
        ? [gridPowerSource, gridCurrentSource, gridVoltageSource, gridModeSource]
        : gridAvailable ? [gridModeSource, gridVoltageSource] : [gridModeSource];

      const homeActive = Number.isFinite(loadPower) && loadPower > 20;
      const gridFlowActive = gridAvailable && Number.isFinite(gridPower) && gridPower > 20;
      const displayedGridVoltage = gridFlowActive && Number.isFinite(gridVoltage)
        ? Math.abs(gridVoltage)
        : 0;
      const displayedHouseVoltage = Number.isFinite(outputVoltage) ? Math.abs(outputVoltage) : null;
      const displayedGridPower = gridAvailable && Number.isFinite(gridPower) ? Math.abs(gridPower) : 0;
      const displayedGridCurrent = gridAvailable && Number.isFinite(gridCurrent) ? Math.abs(gridCurrent) : 0;
      const inverterActive = chartDemoRunning || data.online || pvActive || homeActive || batteryActive;
      const inverterOutputPriority = modeDetails(inverterPrioritySource, {
        0: {label: 'GPB', description: 'modeGpbShort'},
        1: {label: 'PGB', description: 'modePgbShort'},
        2: {label: 'PBG', description: 'modePbgShort'},
        3: {label: 'MKS', description: 'modeMksShort'}
      });
      const inverterState = Number(inverterStateSource?.raw);
      const inverterInputMode = !inverterActive
        ? {label: '—', description: ''}
        : inverterState === 3 && gridAvailable
          ? {label: t('grid'), description: 'modeGridInputShort'}
          : inverterState === 4 && pvActive
            ? {label: 'PV', description: 'modeSolarShort'}
            : inverterState === 5 && batteryDischarging
              ? {label: t('battery'), description: 'modeBatteryInputShort'}
              : inverterState === 6 && generatorActive
                ? {label: t('generator'), description: 'modeGeneratorInputShort'}
                : gridAvailable
                  ? {label: t('grid'), description: 'modeGridInputShort'}
                  : pvActive
                    ? {label: 'PV', description: 'modeSolarShort'}
                    : batteryDischarging
                      ? {label: t('battery'), description: 'modeBatteryInputShort'}
                      : {label: '—', description: ''};
      const inverterBatteryMode = modeDetails(inverterChargeModeSource, {
        0: {label: 'PNG', description: 'modePngShort'},
        1: {label: 'OPV', description: 'modeOpvShort'},
        2: {label: 'PVF', description: 'modePvfShort'}
      });

      setText('#energy-flow-status', chartDemoRunning
        ? t(demoFlowCase || 'demoMode')
        : data.online ? t('online') : t('offline'));
      setText('#energy-solar-registers', chartDemoRunning
        ? t('demoMode')
        : registerText([pvVoltageSource, pvPowerSource], [151, 153, 154, 156]));
      setText('#energy-inverter-registers', registerText(
        [inverterLoadSource, inverterFanSpeedSource, inverterPrioritySource, inverterStateSource, inverterChargeModeSource],
        [94, 801, 529, 325, 324]
      ));
      setText('#energy-home-registers', registerText(
        [outputCurrentSource, loadPowerSource, outputVoltageSource],
        [90, 92, 537]
      ));
      setText('#energy-battery-registers', registerText(
        [batteryVoltageSource, batteryCurrentSource, batteryPowerSources, batterySocSource],
        [129, 130, 134, 339]
      ));
      setText('#energy-grid-registers', registerText(gridRegisterSources, [84, 82, 89, 325]));
      setText('#energy-generator-registers', generatorActive ? t('demoMode') : '—');
      setText('#energy-solar-voltage', Number.isFinite(pvVoltage) ? reading(Math.abs(pvVoltage), 'V', 1) : '— V');
      setText('#energy-solar-power', Number.isFinite(pvPower) ? reading(Math.abs(pvPower), 'W') : '— W');
      setText('#energy-solar-current', Number.isFinite(pvCurrent) ? reading(pvCurrent, 'A', 1) : '— A');
      const solarValues = document.querySelector('.energy-solar-values');
      if (solarValues) solarValues.hidden = !solarDataVisible;
      setText('#energy-solar-direction', !solarDataVisible
        ? t('notConnected')
        : pvActive
          ? pvReceiving ? t('receiving') : t('supplying')
          : t('batteryIdle'));
      setText('#energy-generator-power', generatorActive ? reading(generatorPower, 'W') : '— W');
      setText('#energy-generator-current', generatorActive ? reading(generatorCurrent, 'A', 1) : '— A');
      setText('#energy-generator-voltage', generatorActive ? reading(generatorVoltage, 'V', 1) : '— V');
      const generatorValues = document.querySelector('.energy-generator-values');
      if (generatorValues) generatorValues.hidden = !generatorActive;
      setText('#energy-generator-direction', generatorActive ? t('supplying') : t('notConnected'));
      setText('#energy-inverter-load', Number.isFinite(inverterLoad) ? reading(inverterLoad, '%', 1) : '— %');
      setText('#energy-inverter-fan-speed', Number.isFinite(inverterFanSpeed) ? reading(inverterFanSpeed, '%', 1) : '— %');
      document.querySelector('#energy-inverter-fan-row').classList.toggle(
        'active', Number.isFinite(inverterFanSpeed) && inverterFanSpeed > 0
      );
      setModeText('#energy-inverter-ac-mode', '#energy-inverter-ac-definition', inverterOutputPriority);
      setModeText('#energy-inverter-input-mode', '#energy-inverter-input-definition', inverterInputMode);
      setModeText('#energy-inverter-charge-mode', '#energy-inverter-charge-definition', inverterBatteryMode);
      setText('#energy-home-current', Number.isFinite(outputCurrent) ? reading(Math.abs(outputCurrent), 'A', 2) : '— A');
      setText('#energy-home-voltage', Number.isFinite(displayedHouseVoltage)
        ? reading(displayedHouseVoltage, 'V', 1)
        : '— V');
      setText('#energy-home-power', Number.isFinite(loadPower) ? reading(loadPower, 'W') : '— W');
      setText('#energy-home-direction', homeActive ? t('consuming') : t('batteryIdle'));
      setText('#energy-grid-power', reading(displayedGridPower, 'W'));
      setText('#energy-grid-current', reading(displayedGridCurrent, 'A', 2));
      setText('#energy-grid-voltage', reading(displayedGridVoltage, 'V', 1));
      setText('#energy-grid-direction', gridFlowActive
        ? t('gridSupplying')
        : gridAvailable ? t('gridReady') : t('offline'));
      setText('#energy-battery-current', Number.isFinite(batteryCurrent) ? reading(batteryCurrent, 'A', 1) : '— A');
      setText('#energy-battery-power', Number.isFinite(batteryPower) ? reading(batteryPower, 'W') : '— W');
      setText('#energy-battery-voltage', Number.isFinite(batteryVoltage) ? reading(batteryVoltage, 'V', 1) : '— V');
      const batteryIcon = document.querySelector('#energy-battery-icon');
      const batteryLevel = Number.isFinite(batterySoc)
        ? Math.max(0, Math.min(100, batterySoc))
        : 0;
      batteryIcon?.style.setProperty('--battery-level', `${batteryLevel}%`);
      setText('#energy-battery-percent', Number.isFinite(batterySoc) ? `${Math.round(batteryLevel)}%` : '—');
      batteryIcon?.setAttribute(
        'aria-label',
        Number.isFinite(batterySoc) ? `${t('battery')} ${Math.round(batteryLevel)}%` : `${t('battery')} ${t('noData')}`
      );
      setText('#energy-battery-direction', batteryActive
        ? batteryCharging
          ? t('charging')
          : batteryDischarging ? t('discharging') : t('batteryIdle')
        : t('batteryIdle'));

      setNode('#energy-solar-node', pvActive);
      setNode('#energy-inverter-node', inverterActive);
      setNode('#energy-generator-node', generatorActive);
      setNode('#energy-home-node', homeActive);
      setNode('#energy-grid-node', gridAvailable);
      setNode('#energy-battery-node', Number.isFinite(batteryVoltage) || Number.isFinite(batterySoc));
      // PV is a one-way source and can only supply the inverter.
      setFlow('#energy-pv-flow', pvActive && inverterActive && !pvReceiving, false, pvPower);
      document.querySelector('#energy-pv-flow')?.classList.toggle('disconnected', !pvActive);
      // Home is deliberately one-way: it can consume energy but never supply it.
      setFlow('#energy-home-flow', inverterActive && homeActive, false, loadPower);
      // Generator is a one-way source: animation always travels toward the inverter.
      setFlow(
        '#energy-generator-flow',
        generatorActive && inverterActive,
        true,
        generatorActive ? generatorPower : 0
      );
      document.querySelector('#energy-generator-flow')?.classList.toggle('disconnected', !generatorActive);
      // Grid is a one-way source: animation always travels upward toward the inverter.
      setFlow(
        '#energy-grid-flow',
        gridFlowActive && inverterActive,
        true,
        gridFlowActive ? gridPower : 0
      );
      // Battery and inverter exchange energy in both directions.
      setFlow('#energy-battery-flow', batteryActive && inverterActive, batteryCharging, batteryPower);

      const status = document.querySelector('#energy-flow-status');
      status?.classList.toggle('active', inverterActive);
    }

    function renderLcd(data, registers = data.registers || []) {
      const byNumber = new Map(registers.map(register => [register.register, register]));
      const firstRegister = numbers => numbers
        .map(number => byNumber.get(number))
        .find(register => register?.available);
      const numberValue = numbers => {
        const register = firstRegister(numbers);
        return register ? numericValue(register.display) : null;
      };
      const textValue = numbers => {
        const register = firstRegister(numbers);
        return register ? localizeDataText(register.display) : t('noData');
      };
      const reading = (value, unit, digits = 1) =>
        Number.isFinite(value) ? `${value.toFixed(digits)} ${unit}`.trim() : t('noData');
      const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = value;
      };

      const gridVoltage = numberValue([81, 433]);
      const gridCurrent = numberValue([82, 434]);
      const measuredGridPower = numberValue([84, 437, 436]);
      const frequency = numberValue([83, 435]);
      const outputCurrent = numberValue([90, 539]);
      const inverterLoad = numberValue([94]);
      const gridLowVoltageThreshold = numberValue([16655]);
      const loadPower = numberValue([92]);
      const apparentLoadPower = numberValue([93]);
      const batteryVoltage = numberValue([129, 137, 404, 342]);
      const batteryCurrent = numberValue([130]);
      const batterySoc = numberValue([133, 139, 407, 339]);
      const batteryPowerReading = numberValue([134]);
      const batteryTemperature = numberValue([140, 406]);
      const inverterTemperature = numberValue([818]);
      const maximumChargeVoltage = numberValue([141, 411, 16651, 376, 377]);
      const currentLimit = numberValue([413]);
      const lowSocThreshold = numberValue([415]);
      const statusText = textValue([325, 67]);
      const calculatedBatteryPower = Number.isFinite(batteryVoltage) && Number.isFinite(batteryCurrent)
        ? batteryVoltage * batteryCurrent
        : null;
      const batteryPower = Number.isFinite(batteryPowerReading)
        ? Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
          ? Math.sign(batteryCurrent) * Math.abs(batteryPowerReading)
          : batteryPowerReading
        : calculatedBatteryPower;
      const batteryDirectionFromCurrent = Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3;
      const batteryActiveValue = batteryDirectionFromCurrent
        ? batteryCurrent
        : batteryPower;
      const batteryActivityThreshold = batteryDirectionFromCurrent ? .3 : 20;
      const batteryState = !Number.isFinite(batteryActiveValue) || Math.abs(batteryActiveValue) < batteryActivityThreshold
        ? t('batteryIdle')
        : batteryActiveValue > 0 ? t('charging') : t('discharging');
      const batteryCharging = Number.isFinite(batteryActiveValue) && batteryActiveValue > batteryActivityThreshold;
      const lcdGridVoltagePresent = Number.isFinite(gridVoltage) && Math.abs(gridVoltage) > .5;
      const gridConnected = lcdGridVoltagePresent;
      const displayedGridVoltage = gridConnected && Number.isFinite(gridVoltage) ? gridVoltage : 0;
      const displayedGridCurrent = gridConnected && Number.isFinite(gridCurrent) ? gridCurrent : 0;
      const displayedGridFrequency = gridConnected && Number.isFinite(frequency) ? frequency : 0;
      const gridPower = !gridConnected
        ? 0
        : batteryCharging && Number.isFinite(loadPower)
          ? loadPower + Math.abs(batteryPower || 0)
          : measuredGridPower;

      setText('#lcd-mode', chartDemoRunning ? t('demoMode') : data.online ? t('online') : t('offline'));
      setText('#lcd-grid', reading(gridPower, 'W', 0));
      setText('#lcd-grid-voltage', reading(displayedGridVoltage, 'V'));
      setText('#lcd-grid-current', reading(displayedGridCurrent, 'A', 2));
      setText('#lcd-grid-power', reading(gridPower, 'W', 0));
      setText('#lcd-frequency', reading(displayedGridFrequency, 'Hz', 2));
      setText('#lcd-ac-output-current', reading(outputCurrent, 'A', 2));
      setText('#lcd-inverter-load', reading(inverterLoad, '%', 1));
      setText('#lcd-load-power', reading(loadPower, 'W', 0));
      setText('#lcd-apparent-load-power', reading(apparentLoadPower, 'VA', 0));
      setText('#lcd-grid-low-voltage-threshold', reading(gridLowVoltageThreshold, 'V', 0));
      setText('#lcd-battery-voltage', reading(batteryVoltage, 'V'));
      setText('#lcd-battery-current', reading(batteryCurrent, 'A'));
      setText('#lcd-battery-power', reading(batteryPower, 'W', 0));
      setText('#lcd-soc', reading(batterySoc, '%', 0));
      setText('#lcd-temperature', reading(inverterTemperature, '°C'));
      setText('#lcd-charge-voltage', reading(maximumChargeVoltage, 'V'));
      setText('#lcd-current-limit', Number.isFinite(currentLimit)
        ? `${reading(currentLimit, 'A')} · ${r413BmsFormula(currentLimit)}`
        : t('noData'));
      setText('#lcd-low-soc-threshold', reading(lowSocThreshold, '%', 0));
      setText('#lcd-load', reading(loadPower, 'W', 0));
      setText('#lcd-power', reading(apparentLoadPower, 'VA', 0));
      setText('#lcd-battery-state', batteryState);
      setText('#lcd-system-status', statusText);
      setText('#lcd-status-line', `${data.identifier || t('unknownDevice')} · ${t('updated', {time: data.updated_at})}`);

      const pages = [
        {
          code: 'LCD', title: t('mainDisplay'),
          label1: t('batteryVoltage'), value1: reading(batteryVoltage, 'V'),
          label2: t('acOutputCurrent'), value2: reading(outputCurrent, 'A', 2), help: t('lcdMainPageHelp')
        },
        {
          code: 'P1', title: t('dailyPvEnergy'),
          label1: t('dailyPvEnergy'), value1: reading(numberValue([157]), 'kWh'),
          label2: '', value2: '', help: t('lcdP1Help')
        },
        {
          code: 'P2', title: t('totalPvEnergy'),
          label1: t('totalPvEnergy'), value1: reading(numberValue([158]), 'kWh'),
          label2: '', value2: '', help: t('lcdP2Help')
        },
        {
          code: 'P3', title: t('batteryState'),
          label1: t('batteryVoltage'), value1: reading(batteryVoltage, 'V'),
          label2: t('batteryCurrent'), value2: reading(batteryCurrent, 'A'), help: t('lcdP3Help')
        },
        {
          code: 'P4', title: t('batteryState'),
          label1: t('batteryTemperature'), value1: reading(batteryTemperature, '°C'),
          label2: t('batterySoc'), value2: reading(batterySoc, '%', 0), help: t('lcdP4Help')
        },
        {
          code: 'P5', title: t('availableCapacity'),
          label1: t('availableCapacity'), value1: reading(numberValue([409]), 'Ah'),
          label2: t('possibleBatteryHealth'), value2: reading(numberValue([408]), '%', 0), help: t('lcdP5Help')
        },
        {
          code: 'P6', title: t('maxChargeVoltage'),
          label1: t('maxChargeVoltage'), value1: reading(maximumChargeVoltage, 'V'),
          label2: t('lowerBmsVoltageLimit'), value2: reading(numberValue([346, 349]), 'V'), help: t('lcdP6Help')
        },
        {
          code: 'P7', title: t('currentLimit'),
          label1: t('currentLimit'), value1: Number.isFinite(currentLimit)
            ? `${reading(currentLimit, 'A')} · ${r413BmsFormula(currentLimit)}`
            : t('noData'),
          label2: t('lowSocThreshold'), value2: reading(lowSocThreshold, '%', 0), help: t('lcdP7Help')
        },
        {
          code: 'P8', title: t('alarmFault'),
          label1: t('bmsConnection'), value1: textValue([402]),
          label2: t('alarmFlags'), value2: textValue([418, 419]), help: t('lcdP8Help')
        },
        {
          code: 'P9', title: t('deviceInformation'),
          label1: t('protocolVersion'), value1: textValue([17]),
          label2: t('deviceConfiguration'), value2: textValue([18]), help: t('lcdP9Help')
        },
        {
          code: 'P10', title: localizeDataText('Загальна потужність PV'),
          label1: localizeDataText('Загальна потужність PV'), value1: reading(numberValue([161]), 'W', 0),
          label2: localizeDataText('Навантаження мережі, фаза A'), value2: reading(numberValue([95]), 'W', 0), help: t('lcdV131Help')
        },
        {
          code: 'P11', title: 'PV1 / PV2',
          label1: localizeDataText('Струм заряджання від PV1'), value1: reading(numberValue([159]), 'A'),
          label2: localizeDataText('Струм заряджання від PV2'), value2: reading(numberValue([160]), 'A'), help: t('lcdV131Help')
        },
        {
          code: 'P12', title: localizeDataText('Енергія PV за місяць'),
          label1: localizeDataText('Енергія PV за місяць'), value1: reading(numberValue([162]), 'kWh'),
          label2: localizeDataText('Енергія PV за рік'), value2: reading(numberValue([163]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P13', title: t('generator'),
          label1: localizeDataText('Напруга генератора, фаза A'), value1: reading(numberValue([85]), 'V'),
          label2: localizeDataText('Потужність генератора, фаза A'), value2: reading(numberValue([88]), 'W', 0), help: t('lcdV131Help')
        },
        {
          code: 'P14', title: t('generator'),
          label1: localizeDataText('Струм генератора, фаза A'), value1: reading(numberValue([86]), 'A', 2),
          label2: localizeDataText('Частота генератора, фаза A'), value2: reading(numberValue([87]), 'Hz', 2), help: t('lcdV131Help')
        },
        {
          code: 'P15', title: localizeDataText('Загальна енергія заряджання'),
          label1: localizeDataText('Енергія заряджання за день'), value1: reading(numberValue([164]), 'kWh'),
          label2: localizeDataText('Загальна енергія заряджання'), value2: reading(numberValue([167]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P16', title: localizeDataText('Загальна енергія розряджання'),
          label1: localizeDataText('Енергія розряджання за день'), value1: reading(numberValue([168]), 'kWh'),
          label2: localizeDataText('Загальна енергія розряджання'), value2: reading(numberValue([171]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P17', title: localizeDataText('Загальна енергія навантаження'),
          label1: localizeDataText('Енергія навантаження за день'), value1: reading(numberValue([176]), 'kWh'),
          label2: localizeDataText('Загальна енергія навантаження'), value2: reading(numberValue([179]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P18', title: localizeDataText('Загальна енергія віддачі в мережу'),
          label1: localizeDataText('Енергія віддачі в мережу за день'), value1: reading(numberValue([180]), 'kWh'),
          label2: localizeDataText('Загальна енергія віддачі в мережу'), value2: reading(numberValue([183]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P19', title: localizeDataText('Загальна енергія споживання з мережі'),
          label1: localizeDataText('Енергія споживання з мережі за день'), value1: reading(numberValue([184]), 'kWh'),
          label2: localizeDataText('Загальна енергія споживання з мережі'), value2: reading(numberValue([187]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P20', title: localizeDataText('Енергія заряджання за місяць'),
          label1: localizeDataText('Енергія заряджання за місяць'), value1: reading(numberValue([165]), 'kWh'),
          label2: localizeDataText('Енергія заряджання за рік'), value2: reading(numberValue([166]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P21', title: localizeDataText('Енергія розряджання за місяць'),
          label1: localizeDataText('Енергія розряджання за місяць'), value1: reading(numberValue([169]), 'kWh'),
          label2: localizeDataText('Енергія розряджання за рік'), value2: reading(numberValue([170]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P22', title: localizeDataText('Енергія навантаження за місяць'),
          label1: localizeDataText('Енергія навантаження за місяць'), value1: reading(numberValue([177]), 'kWh'),
          label2: localizeDataText('Енергія навантаження за рік'), value2: reading(numberValue([178]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P23', title: localizeDataText('Енергія віддачі в мережу за місяць'),
          label1: localizeDataText('Енергія віддачі в мережу за місяць'), value1: reading(numberValue([181]), 'kWh'),
          label2: localizeDataText('Енергія віддачі в мережу за рік'), value2: reading(numberValue([182]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P24', title: localizeDataText('Енергія споживання з мережі за місяць'),
          label1: localizeDataText('Енергія споживання з мережі за місяць'), value1: reading(numberValue([185]), 'kWh'),
          label2: localizeDataText('Енергія споживання з мережі за рік'), value2: reading(numberValue([186]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P25', title: localizeDataText('Потужність навантаження на виході, фаза A'),
          label1: localizeDataText('Потужність навантаження на виході, фаза A'), value1: reading(numberValue([188]), 'W', 0),
          label2: localizeDataText('Потужність навантаження на виході, фаза B'), value2: reading(numberValue([189]), 'W', 0), help: t('lcdV131Help')
        },
        {
          code: 'P26', title: localizeDataText('Температура PV2'),
          label1: localizeDataText('Потужність навантаження на виході, фаза C'), value1: reading(numberValue([190]), 'W', 0),
          label2: localizeDataText('Температура PV2'), value2: reading(numberValue([823]), '°C'), help: t('lcdV131Help')
        }
      ];
      const page = pages[lcdPageIndex] || pages[0];
      setText('#lcd-page-code', page.code);
      setText('#lcd-page-title', page.title);
      setText('#lcd-page-label-1', page.label1);
      setText('#lcd-page-value-1', page.value1);
      setText('#lcd-page-label-2', page.label2);
      setText('#lcd-page-value-2', page.value2);
      setText('#lcd-page-description', lcdEnterNotice ? t('settingsReadOnly') : page.help);
      document.querySelector('#lcd-page-reading-2').hidden = !page.label2;

      const active = (selector, enabled) =>
        document.querySelector(selector)?.classList.toggle('active', Boolean(enabled));
      active('#lcd-grid-node', gridConnected);
      active('#lcd-grid-arrow', gridConnected && Number.isFinite(gridPower) && Math.abs(gridPower) > 20);
      active('#lcd-inverter-node', chartDemoRunning || data.online);
      active('#lcd-load-node', Number.isFinite(loadPower) && loadPower > 20);
      active('#lcd-load-arrow', Number.isFinite(loadPower) && loadPower > 20);
      active('#lcd-ac-output-card', Number.isFinite(outputCurrent) && outputCurrent > .05);
      active('#lcd-battery-card', Number.isFinite(batteryVoltage) && batteryVoltage > 20);
      active('#lcd-soc-card', Number.isFinite(batterySoc));
    }

    function render(data) {
      lastData = data;
      document.querySelector('#identifier').textContent = data.identifier || t('unknownDevice');
      const status = document.querySelector('#status');
      status.classList.toggle('online', chartDemoRunning || (data.online && !data.paused));
      status.classList.toggle('paused', !chartDemoRunning && data.paused);
      status.querySelector('.status-label').textContent =
        chartDemoRunning
          ? t('demoMode')
          : data.paused ? t('paused') : data.online ? t('online') : t('offline');
      const appToggle = document.querySelector('#app-toggle');
      appToggle.textContent = data.paused ? t('startMonitoring') : t('stopMonitoring');
      appToggle.classList.toggle('start', data.paused);
      document.querySelector('#updated').textContent =
        t('updated', {time: localizeDataText(data.updated_at)});
      document.querySelector('#cycle').textContent =
        data.paused
          ? t('cyclePaused', {cycle: data.cycle_id})
          : t('cycleReads', {
              cycle: data.cycle_id,
              seconds: data.cycle_seconds.toFixed(2),
              reads: data.successful
            });
      const totalVisitors = Number(data.site_visits || 0);
      const numberLocale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      document.querySelector('#site-visits').textContent =
        t('visitors', {
          count: totalVisitors.toLocaleString(numberLocale),
          date: data.site_visits_date
        });
      if (lastLoggedSiteVisits !== totalVisitors) {
        const visitDetails = {};
        visitDetails[t('totalVisitorsLabel')] = totalVisitors;
        visitDetails[t('dateLabel')] = data.site_visits_date;
        visitDetails[t('openedLabel')] = new Date().toISOString();
        visitDetails[t('referrerLabel')] = document.referrer || t('direct');
        visitDetails[t('browserLanguageLabel')] = navigator.language;
        visitDetails[t('browserLabel')] = navigator.userAgent;
        visitDetails[t('viewportLabel')] = `${window.innerWidth}x${window.innerHeight}`;
        console.log(t('visitConsole'), visitDetails);
        lastLoggedSiteVisits = totalVisitors;
      }
      document.querySelector('#poll-rate').value = data.poll_rate_index;
      document.querySelector('#read-mode').value = data.read_mode;
      const error = document.querySelector('#error');
      const connectionError = chartDemoRunning ? '' : data.error;
      error.textContent = connectionError
        ? t('connectionError', {error: localizeDataText(data.error)})
        : '';
      error.classList.toggle('show', Boolean(connectionError));
      renderRegisterLog(data.register_log);
      renderSolarEnergy(data.solar_energy);
      renderRegisters(data.registers);
      const displayedRegisters = chartDemoRunning && demoRegisterRows ? demoRegisterRows : data.registers;
      renderEnergyFlow(data, displayedRegisters);
      renderLcd(data, displayedRegisters);
      updateChartDefinitions(data);
    }

    async function refresh() {
      if (refreshInFlight) return;
      refreshInFlight = true;
      refreshController = new AbortController();
      try {
        const response = await fetch('/api/state', {
          cache: 'no-store',
          signal: refreshController.signal
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        lastData = data;
        recordChartSamples(data);
        if (!chartDemoRunning) render(data);
      } catch (error) {
        if (error.name === 'AbortError') return;
        if (chartDemoRunning) return;
        const box = document.querySelector('#error');
        box.textContent = t('connectionLost', {error: error.message});
        box.classList.add('show');
      } finally {
        refreshInFlight = false;
        refreshController = null;
        if (!lastData?.paused) {
          scheduleRefresh();
        } else if (refreshTimer !== null) {
          window.clearTimeout(refreshTimer);
          refreshTimer = null;
        }
      }
    }

    function scheduleRefresh(delay = null) {
      if (refreshTimer !== null) window.clearTimeout(refreshTimer);
      const selectedIndex = Number(document.querySelector('#poll-rate').value);
      const milliseconds = delay ?? requestIntervals[selectedIndex] ?? 2000;
      refreshTimer = window.setTimeout(refresh, milliseconds);
    }

    async function updateSetting(setting, value) {
      await fetch('/api/settings', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({[setting]: value})
      });
      if (setting === 'paused' && value === true) {
        if (refreshTimer !== null) window.clearTimeout(refreshTimer);
        refreshTimer = null;
        refreshController?.abort();
      } else {
        scheduleRefresh(0);
      }
    }

    let registerMapFeedbackTimer = null;
    async function uploadRegisterMap(file) {
      const button = document.querySelector('#register-map-upload-button');
      const input = document.querySelector('#register-map-file');
      if (!file) return;
      if (file.size > 1024 * 1024) {
        button.textContent = t('registerMapFileTooLarge');
        input.value = '';
        registerMapFeedbackTimer = window.setTimeout(() => {
          button.textContent = t('uploadRegisterMap');
          registerMapFeedbackTimer = null;
        }, 5000);
        return;
      }
      if (registerMapFeedbackTimer !== null) window.clearTimeout(registerMapFeedbackTimer);
      button.disabled = true;
      button.textContent = t('registerMapUploading');
      try {
        const response = await fetch('/api/register-map', {
          method: 'POST',
          headers: {'Content-Type': 'text/csv; charset=utf-8'},
          body: file
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        button.textContent = t('registerMapUploaded', {count: result.count});
        scheduleRefresh(0);
      } catch (error) {
        const message = t('registerMapUploadError', {error: error.message});
        button.textContent = message;
        button.title = message;
      } finally {
        button.disabled = false;
        input.value = '';
        registerMapFeedbackTimer = window.setTimeout(() => {
          button.textContent = t('uploadRegisterMap');
          button.title = t('registerMapHelp');
          registerMapFeedbackTimer = null;
        }, 5000);
      }
    }

    function wait(milliseconds) {
      return new Promise(resolve => setTimeout(resolve, milliseconds));
    }

    function showView(view) {
      currentView = ['dashboard', 'charts', 'lcd'].includes(view) ? view : 'dashboard';
      document.querySelector('#dashboard-view').hidden = currentView !== 'dashboard';
      document.querySelector('#charts-view').hidden = currentView !== 'charts';
      document.querySelector('#lcd-view').hidden = currentView !== 'lcd';
      document.querySelectorAll('.view-tab').forEach(button => {
        const active = button.dataset.view === currentView;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
      });
      if (currentView === 'charts') requestAnimationFrame(drawAllCharts);
      if (currentView === 'dashboard' && chartDemoRunning && lastData && demoRegisterRows) {
        requestAnimationFrame(() => renderEnergyFlow(lastData, demoRegisterRows));
      }
    }

    async function recordDemoLcdKey(key) {
      if (!chartDemoRunning || !lastData?.register_log?.active) return;
      const page = lcdPageIndex === 0 ? 'LCD' : `P${lcdPageIndex}`;
      try {
        const response = await fetch('/api/register-log', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            action: 'lcd_key',
            key,
            page,
            demo_case: demoFlowCase || 'demoMode'
          })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        lastData.register_log = result;
        renderRegisterLog(result);
      } catch (error) {
        const status = document.querySelector('#register-log-status');
        status.className = 'logger-status error-text';
        status.textContent = t('registerLogRequestError', {error: localizeDataText(error.message)});
      }
    }

    function handleLcdKey(key) {
      if (key === 'escape') {
        lcdPageIndex = 0;
        lcdEnterNotice = false;
      } else if (key === 'up') {
        lcdPageIndex = lcdPageIndex <= 1 ? lcdInformationPageCount : lcdPageIndex - 1;
        lcdEnterNotice = false;
      } else if (key === 'down') {
        lcdPageIndex = lcdPageIndex === 0 || lcdPageIndex >= lcdInformationPageCount
          ? 1
          : lcdPageIndex + 1;
        lcdEnterNotice = false;
      } else if (key === 'enter') {
        lcdEnterNotice = true;
      } else {
        return;
      }
      if (lastData) {
        renderLcd(lastData, chartDemoRunning && demoRegisterRows ? demoRegisterRows : lastData.registers);
      }
      void recordDemoLcdKey(key);
    }

    function applyLanguage(language, save = true) {
      currentLanguage = ['uk', 'ru', 'en'].includes(language) ? language : 'uk';
      document.documentElement.lang = currentLanguage;
      document.querySelectorAll('[data-i18n]').forEach(element => {
        element.textContent = t(element.dataset.i18n);
      });
      document.querySelectorAll('[data-i18n-aria]').forEach(element => {
        element.setAttribute('aria-label', t(element.dataset.i18nAria));
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder));
      });
      document.querySelectorAll('[data-i18n-title]').forEach(element => {
        element.setAttribute('title', t(element.dataset.i18nTitle));
      });
      document.querySelectorAll('.language-option').forEach(button => {
        const active = button.dataset.language === currentLanguage;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      document.querySelector('#theme-name').textContent =
        document.documentElement.dataset.theme === 'light' ? t('themeLight') : t('themeDark');
      showView(currentView);
      if (!chartDemoRunning) {
        document.querySelectorAll('.all-data-demo-button').forEach(button => {
          button.textContent = t('runDemo');
        });
      }
      if (save) {
        try {
          window.localStorage.setItem('solar-invertor-language', currentLanguage);
        } catch {
          // Language switching still works when browser storage is unavailable.
        }
      }
      lastLoggedSiteVisits = null;
      if (lastData) {
        document.querySelector('#gauges').innerHTML = '';
        render(lastData);
        renderChartValueList();
        renderGaugePickerList();
        renderChartCards();
        renderDashboardValues();
      } else {
        document.querySelector('#app-toggle').textContent = t('stopMonitoring');
        document.querySelector('#status .status-label').textContent = t('offline');
        document.querySelector('#cycle').textContent = t('cycleInitial');
        document.querySelector('#site-visits').textContent = t('visitorsInitial');
        document.querySelector('#updated').textContent = t('notUpdated');
        renderChartCards();
      }
      requestAnimationFrame(drawAllCharts);
    }

    function initialLanguage() {
      try {
        const savedLanguage = window.localStorage.getItem('solar-invertor-language');
        if (['uk', 'ru', 'en'].includes(savedLanguage)) return savedLanguage;
      } catch {
        // Use Ukrainian when browser storage is unavailable.
      }
      return 'uk';
    }

    function applyTheme(theme, save = true) {
      const selectedTheme = theme === 'light' ? 'light' : 'dark';
      document.documentElement.dataset.theme = selectedTheme;
      document.querySelector('#theme-toggle').checked = selectedTheme === 'light';
      document.querySelector('#theme-name').textContent =
        selectedTheme === 'light' ? t('themeLight') : t('themeDark');
      if (save) {
        try {
          window.localStorage.setItem('inverter-theme', selectedTheme);
        } catch {
          // Theme still changes when browser storage is unavailable.
        }
      }
      requestAnimationFrame(drawAllCharts);
    }

    function initialTheme() {
      try {
        const savedTheme = window.localStorage.getItem('inverter-theme');
        if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme;
      } catch {
        // Fall through to the system preference.
      }
      return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    applyTheme(initialTheme(), false);
    applyLanguage(initialLanguage(), false);

    document.querySelector('#poll-rate').addEventListener('change', event =>
      updateSetting('poll_rate_index', Number(event.target.value)));
    document.querySelector('#read-mode').addEventListener('change', event =>
      updateSetting('read_mode', event.target.value));
    document.querySelector('#demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#chart-demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#manage-values-button').addEventListener('click', openGaugePicker);
    document.querySelector('#register-log-start').addEventListener('click', () => updateRegisterLog('start'));
    document.querySelector('#register-log-stop').addEventListener('click', () => updateRegisterLog('stop'));
    document.querySelector('#register-log-mark').addEventListener('click', () =>
      updateRegisterLog('mark', document.querySelector('#register-log-note').value));
    document.querySelector('#register-log-note').addEventListener('keydown', event => {
      if (event.key === 'Enter') updateRegisterLog('mark', event.currentTarget.value);
    });
    document.querySelector('#register-map-upload-button').addEventListener('click', () =>
      document.querySelector('#register-map-file').click());
    document.querySelector('#register-map-file').addEventListener('change', event =>
      void uploadRegisterMap(event.currentTarget.files?.[0]));
    document.querySelector('#search').addEventListener('input', () =>
      demoRegisterRows
        ? renderRegisters(demoRegisterRows)
        : lastData && renderRegisters(lastData.registers));
    document.querySelector('.view-tabs').addEventListener('click', event => {
      const tab = event.target.closest('.view-tab[data-view]');
      if (tab) showView(tab.dataset.view);
    });
    document.querySelector('.lcd-controls').addEventListener('click', event => {
      const button = event.target.closest('[data-lcd-key]');
      if (button) handleLcdKey(button.dataset.lcdKey);
    });
    window.addEventListener('keydown', event => {
      if (currentView !== 'lcd' || event.target?.closest?.('input, select, textarea')) return;
      const key = ({Escape:'escape', ArrowUp:'up', ArrowDown:'down', Enter:'enter'})[event.key];
      if (!key) return;
      event.preventDefault();
      handleLcdKey(key);
    });
    document.querySelector('#app-toggle').addEventListener('click', async event => {
      if (!lastData) return;
      const toggleButton = event.currentTarget;
      const paused = !lastData.paused;
      lastData.paused = paused;
      render(lastData);
      toggleButton.disabled = true;
      try {
        await updateSetting('paused', paused);
      } finally {
        toggleButton.disabled = false;
      }
    });
    document.querySelector('#theme-toggle').addEventListener('change', event =>
      applyTheme(event.target.checked ? 'light' : 'dark'));
    document.querySelector('.language-switch').addEventListener('click', event => {
      const button = event.target.closest('button[data-language]');
      if (button) applyLanguage(button.dataset.language);
    });
    document.querySelector('#chart-search').addEventListener('input', renderChartValueList);
    document.querySelector('#chart-select-all').addEventListener('click', selectAllGaugeSelections);
    document.querySelector('#chart-clear-all').addEventListener('click', clearGaugeSelections);
    document.querySelector('#dashboard-clear-gauges').addEventListener('click', clearGaugeSelections);
    document.querySelector('#chart-value-list').addEventListener('change', event => {
      const checkbox = event.target.closest('input[data-value-key]');
      if (!checkbox) return;
      const key = checkbox.dataset.valueKey;
      if (checkbox.checked) {
        dashboardSelections.add(key);
        chartSelections.add(key);
        chartHistory.set(key, []);
      } else {
        dashboardSelections.delete(key);
        chartSelections.delete(key);
        chartHistory.delete(key);
      }
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderGaugePickerList();
    });
    document.querySelector('#gauge-picker-search').addEventListener('input', renderGaugePickerList);
    document.querySelector('#select-all-gauges').addEventListener('click', selectAllGaugeSelections);
    document.querySelector('#clear-all-gauges').addEventListener('click', clearGaugeSelections);
    document.querySelector('#gauge-picker-list').addEventListener('change', event => {
      const checkbox = event.target.closest('input[data-picker-value-key]');
      if (!checkbox) return;
      const key = checkbox.dataset.pickerValueKey;
      if (checkbox.checked) {
        dashboardSelections.add(key);
        chartSelections.add(key);
        chartHistory.set(key, []);
      } else {
        dashboardSelections.delete(key);
        chartSelections.delete(key);
        chartHistory.delete(key);
      }
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
    });
    document.querySelector('[data-close-gauge-picker]').addEventListener('click', () =>
      document.querySelector('#gauge-picker').close());
    document.querySelector('#gauge-picker').addEventListener('click', event => {
      if (event.target === event.currentTarget) event.currentTarget.close();
    });
    const gaugeHost = document.querySelector('#gauges');
    let draggedGauge = null;
    let pointerDraggedGauge = null;
    let pointerDragHandle = null;

    function saveDashboardOrderFromCards() {
      const orderedKeys = [...gaugeHost.querySelectorAll('[data-dashboard-key]')]
        .map(card => card.dataset.dashboardKey)
        .filter(key => dashboardSelections.has(key));
      dashboardSelections.clear();
      orderedKeys.forEach(key => dashboardSelections.add(key));
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      gaugeHost.dataset.keys = dashboardGaugeSignature(dashboardGaugeItems());
    }

    function placeGaugeAtPointer(card, target, clientX, clientY) {
      gaugeHost.querySelectorAll('.drag-target').forEach(item => item.classList.remove('drag-target'));
      if (!target || target === card || !gaugeHost.contains(target)) return;
      target.classList.add('drag-target');
      const bounds = target.getBoundingClientRect();
      const cardBounds = card.getBoundingClientRect();
      const sameRow = Math.abs(bounds.top - cardBounds.top) < bounds.height / 2;
      const placeAfter = sameRow
        ? clientX > bounds.left + bounds.width / 2
        : clientY > bounds.top + bounds.height / 2;
      target[placeAfter ? 'after' : 'before'](card);
    }

    gaugeHost.addEventListener('dragstart', event => {
      const card = event.target.closest('.gauge-card[data-dashboard-key]');
      if (!card) return;
      draggedGauge = card;
      card.classList.add('dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', card.dataset.dashboardKey);
    });
    gaugeHost.addEventListener('dragover', event => {
      if (!draggedGauge) return;
      event.preventDefault();
      const target = event.target.closest('.gauge-card[data-dashboard-key]');
      placeGaugeAtPointer(draggedGauge, target, event.clientX, event.clientY);
    });
    gaugeHost.addEventListener('drop', event => {
      if (!draggedGauge) return;
      event.preventDefault();
      saveDashboardOrderFromCards();
    });
    gaugeHost.addEventListener('dragend', () => {
      gaugeHost.querySelectorAll('.dragging, .drag-target').forEach(card =>
        card.classList.remove('dragging', 'drag-target'));
      draggedGauge = null;
    });

    gaugeHost.addEventListener('pointerdown', event => {
      const handle = event.target.closest('.drag-handle');
      if (!handle || event.button !== 0 || event.isPrimary === false) return;
      const card = handle.closest('.gauge-card[data-dashboard-key]');
      if (!card) return;
      event.preventDefault();
      pointerDraggedGauge = card;
      pointerDragHandle = handle;
      card.classList.add('pointer-dragging');
      handle.setPointerCapture(event.pointerId);
    });

    gaugeHost.addEventListener('pointermove', event => {
      if (!pointerDraggedGauge || !pointerDragHandle) return;
      event.preventDefault();
      if (event.clientY < 70) window.scrollBy(0, -14);
      if (event.clientY > window.innerHeight - 70) window.scrollBy(0, 14);

      const previousVisibility = pointerDraggedGauge.style.visibility;
      pointerDraggedGauge.style.visibility = 'hidden';
      const elementBelow = document.elementFromPoint(event.clientX, event.clientY);
      pointerDraggedGauge.style.visibility = previousVisibility;
      const target = elementBelow?.closest('.gauge-card[data-dashboard-key]') || null;
      placeGaugeAtPointer(pointerDraggedGauge, target, event.clientX, event.clientY);
    });

    function finishPointerGaugeDrag(event) {
      if (!pointerDraggedGauge) return;
      if (pointerDragHandle?.hasPointerCapture(event.pointerId)) {
        pointerDragHandle.releasePointerCapture(event.pointerId);
      }
      pointerDraggedGauge.classList.remove('pointer-dragging');
      gaugeHost.querySelectorAll('.drag-target').forEach(card => card.classList.remove('drag-target'));
      pointerDraggedGauge = null;
      pointerDragHandle = null;
      saveDashboardOrderFromCards();
    }

    gaugeHost.addEventListener('pointerup', finishPointerGaugeDrag);
    gaugeHost.addEventListener('pointercancel', finishPointerGaugeDrag);

    gaugeHost.addEventListener('click', event => {
      if (event.target.closest('[data-open-gauge-picker]')) {
        openGaugePicker();
        return;
      }
      const button = event.target.closest('button[data-remove-dashboard]');
      if (!button) return;
      const key = button.dataset.removeDashboard;
      dashboardSelections.delete(key);
      chartSelections.delete(key);
      chartHistory.delete(key);
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
      renderGaugePickerList();
    });
    window.addEventListener('resize', () => {
      if (!document.querySelector('#charts-view').hidden) drawAllCharts();
    });
    const initialData = /*__INITIAL_STATE__*/null;
    if (initialData) {
      lastData = initialData;
      render(initialData);
      recordChartSamples(initialData);
      if (!initialData.paused) {
        window.addEventListener('load', () => scheduleRefresh(), {once: true});
      }
    } else {
      refresh();
    }
    document.documentElement.classList.remove('booting');
  </script>
</body>
</html>
"""
