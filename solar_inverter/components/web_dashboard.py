from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ..services import inverter_service
from ..services.inverter_service import *
from .dashboard_template import WEB_DASHBOARD

def web_state() -> dict[str, Any]:
    """Return a JSON-safe snapshot for the browser."""
    with state_lock:
        snapshot = dict(state)
        values = dict(state["values"])

    meters = []
    for register, fallbacks, label, minimum, maximum, unit in METER_DEFINITIONS:
        value, source = meter_value(values, register, fallbacks)
        if value is None:
            value = 0.0
            source = "Немає даних mbpoll"
        meters.append({
            "register": register,
            "label": label,
            "minimum": minimum,
            "maximum": maximum,
            "unit": unit,
            "value": value,
            "source": source,
        })

    registers = []
    all_registers = sorted(set(KNOWN_REGISTERS) | set(values))
    for register in all_registers:
        raw = values.get(register)
        name, scale, unit, signed, group = REGISTER_CONFIG.get(
            register, (f"Регістр {register}", 1.0, "", False, "Сире")
        )
        if raw is None:
            display = "0"
        else:
            name, display, unit, _, group = normalize(register, raw)
        registers.append({
            "register": register,
            "group": group,
            "name": name,
            "display": display,
            "unit": unit,
            "scale": scale,
            "signed": signed,
            "raw": raw,
            "available": raw is not None,
        })

    return {
        "online": bool(snapshot["online"]),
        "updated_at": snapshot["updated_at"],
        "cycle_seconds": snapshot["cycle_seconds"],
        "cycle_id": snapshot["cycle_id"],
        "poll_rate_index": snapshot["poll_rate_index"],
        "read_mode": snapshot["read_mode"],
        "requests": snapshot["requests"],
        "successful": snapshot["successful"],
        "failed": snapshot["ошибок"],
        "error": snapshot["error"],
        "identifier": snapshot["identifier"],
        "paused": bool(snapshot["paused"]),
        "site_visits": inverter_service.site_visit_total,
        "site_visits_date": datetime.now(MADRID_TIME_ZONE).strftime("%d.%m.%Y"),
        "solar_energy": solar_energy_summary(),
        "register_log": register_log_status(),
        "meters": meters,
        "registers": registers,
    }

def safe_console_print(message: str) -> None:
    """Print localized text without failing on a legacy Windows code page."""
    console_encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_message = message.encode(
        console_encoding, errors="backslashreplace"
    ).decode(console_encoding)
    print(safe_message, flush=True)


def log_visit_to_console(
    handler: BaseHTTPRequestHandler, new_visitor: bool
) -> None:
    """Write request details to the private server terminal only."""
    peer = str(handler.client_address[0])
    forwarded = handler.headers.get("X-Forwarded-For", "")
    source = (
        forwarded.split(",", 1)[0].strip()
        if peer in {"127.0.0.1", "::1"} and forwarded
        else peer
    )
    details = {
        "подія": "відвідування_панелі",
        "дата": datetime.now(MADRID_TIME_ZONE).isoformat(timespec="seconds"),
        "усього_відвідувачів": inverter_service.site_visit_total,
        "новий_відвідувач": new_visitor,
        "джерело": source[:100],
        "ідентифікатор": (
            handler.headers.get("Tailscale-User-Login")
            or handler.headers.get("Tailscale-User-Name")
            or "публічний/анонімний"
        )[:160],
        "джерело_переходу": handler.headers.get("Referer", "прямий перехід")[:500],
        "браузер": handler.headers.get("User-Agent", "невідомо")[:500],
    }
    message = (
        "ВІДВІДУВАЧ "
        + json.dumps(details, ensure_ascii=False, separators=(",", ":"))
    )
    safe_console_print(message)


class DashboardHandler(BaseHTTPRequestHandler):
    """Serve the dashboard and its small JSON API."""

    def send_content(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # Browsers and reverse proxies may cancel an obsolete polling request.
            return

    def do_GET(self) -> None:
        request_path = self.path.split("?", 1)[0]
        if request_path in {"/favicon.png", "/favicon.ico"}:
            try:
                self.send_content(FAVICON_PATH.read_bytes(), "image/png")
            except OSError:
                self.send_content(b"", "image/png", HTTPStatus.NOT_FOUND)
            return

        if request_path == "/":
            new_visitor = not visitor_was_counted(
                self.headers.get("Cookie", "")
            )
            if new_visitor:
                increment_site_visits()
            log_visit_to_console(self, new_visitor)
            initial_state = json.dumps(
                web_state(), ensure_ascii=False, separators=(",", ":")
            ).replace("<", "\\u003c")
            page = WEB_DASHBOARD.replace(
                "/*__INITIAL_STATE__*/null", initial_state, 1
            )
            response_headers: dict[str, str] = {}
            if new_visitor:
                cookie = (
                    f"{COUNTED_VISITOR_COOKIE}=1; Path=/; Max-Age=31536000; "
                    "HttpOnly; SameSite=Lax"
                )
                if (
                    self.headers.get("X-Forwarded-Proto", "").lower() == "https"
                    or self.headers.get("Host", "").endswith(".ts.net")
                ):
                    cookie += "; Secure"
                response_headers["Set-Cookie"] = cookie
            self.send_content(
                page.encode("utf-8"),
                "text/html; charset=utf-8",
                extra_headers=response_headers,
            )
            return
        if request_path == "/api/state":
            body = json.dumps(web_state(), ensure_ascii=False).encode("utf-8")
            self.send_content(body, "application/json; charset=utf-8")
            return
        if request_path == "/api/register-log/download":
            with inverter_service.register_log_lock:
                path = inverter_service.register_log_path
                if path is None and REGISTER_LOG_DIRECTORY.exists():
                    path = max(
                        REGISTER_LOG_DIRECTORY.glob("register_changes_*.csv"),
                        key=lambda candidate: candidate.stat().st_mtime,
                        default=None,
                    )
                if inverter_service.register_log_file is not None:
                    inverter_service.register_log_file.flush()
            if path is None or not path.exists():
                self.send_content(
                    '{"error":"журнал ще не створено"}'.encode("utf-8"),
                    "application/json; charset=utf-8",
                    HTTPStatus.NOT_FOUND,
                )
                return
            try:
                self.send_content(
                    path.read_bytes(),
                    "text/csv; charset=utf-8",
                    extra_headers={
                        "Content-Disposition": f'attachment; filename="{path.name}"'
                    },
                )
            except OSError as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.INTERNAL_SERVER_ERROR
                )
            return
        self.send_content(
            '{"error":"не знайдено"}'.encode("utf-8"),
            "application/json",
            HTTPStatus.NOT_FOUND,
        )

    def do_POST(self) -> None:
        if self.path == "/api/register-log":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                action = payload.get("action")
                if action == "start":
                    result = start_register_log(
                        str(payload.get("language", "uk")),
                        payload.get("translations"),
                    )
                elif action == "stop":
                    result = stop_register_log()
                elif action == "mark":
                    with state_lock:
                        cycle_id = int(state["cycle_id"])
                    result = record_register_log_note(
                        str(payload.get("note", "")), cycle_id
                    )
                elif action == "lcd_key":
                    with state_lock:
                        cycle_id = int(state["cycle_id"])
                    result = record_demo_lcd_key(
                        str(payload.get("key", "")),
                        str(payload.get("page", "")),
                        str(payload.get("demo_case", "")),
                        cycle_id,
                    )
                else:
                    raise ValueError("action має бути start, stop, mark або lcd_key")
                status = (
                    HTTPStatus.INTERNAL_SERVER_ERROR
                    if result.get("error")
                    else HTTPStatus.OK
                )
                body = json.dumps(result, ensure_ascii=False).encode("utf-8")
                self.send_content(body, "application/json; charset=utf-8", status)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                body = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_content(
                    body, "application/json; charset=utf-8", HTTPStatus.BAD_REQUEST
                )
            return

        if self.path != "/api/settings":
            self.send_content(
                '{"error":"не знайдено"}'.encode("utf-8"),
                "application/json",
                HTTPStatus.NOT_FOUND,
            )
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            with state_lock:
                if "poll_rate_index" in payload:
                    index = int(payload["poll_rate_index"])
                    if not 0 <= index < len(POLL_RATES):
                        raise ValueError("неправильний інтервал опитування")
                    state["poll_rate_index"] = index
                if "read_mode" in payload:
                    mode = str(payload["read_mode"])
                    if mode not in {"fast", "compatible"}:
                        raise ValueError("неправильний режим читання")
                    state["read_mode"] = mode
                if "paused" in payload:
                    paused = payload["paused"]
                    if not isinstance(paused, bool):
                        raise ValueError("paused має бути true або false")
                    state["paused"] = paused
            poll_wake_event.set()
            self.send_content(b'{"ok":true}', "application/json")
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            body = json.dumps({"error": str(error)}).encode("utf-8")
            self.send_content(body, "application/json", HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_web_dashboard() -> None:
    host = os.environ.get("INVERTER_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("INVERTER_WEB_PORT", "8080"))
    initialise_statistics()
    maintain_register_log_storage(force=True)
    register_log_storage_stop_event.clear()
    storage_worker = threading.Thread(
        target=register_log_storage_worker,
        name="register-log-storage",
        daemon=True,
    )
    storage_worker.start()
    worker = threading.Thread(target=poll_worker, name="inverter-poller", daemon=True)
    worker.start()
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    safe_console_print(f"Solar Inverter Web: http://localhost:{port}")
    safe_console_print(
        f"Прослуховування {host}:{port} — натисніть Ctrl+C для зупинки"
    )
    if inverter_service.stats_error:
        safe_console_print(f"Лічильник відвідувачів вимкнено: {inverter_service.stats_error}")
    else:
        safe_console_print(
            f"Лічильник: {inverter_service.site_visit_total} відвідувачів · {STATS_DB_PATH}"
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        register_log_storage_stop_event.set()
        stop_register_log()
        flush_solar_energy()
        with state_lock:
            state["stop"] = True
        poll_wake_event.set()
        server.server_close()
