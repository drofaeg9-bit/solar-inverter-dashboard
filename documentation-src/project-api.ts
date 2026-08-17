/**
 * Documentation-only TypeScript contracts for the Python dashboard.
 *
 * Compodoc parses TypeScript but cannot introspect Python. These declarations
 * describe the public JSON contracts implemented by
 * `solar_inverter/components/web_dashboard.py`; they are not application code.
 */

/** A normalized Modbus register returned by `GET /api/state`. */
export interface RegisterReading {
  /** Holding-register address. */
  register: number;
  /** Human-readable register name. */
  name: string;
  /** Raw unsigned 16-bit value. */
  raw: number;
  /** Formatted engineering value or localized status text. */
  display: string;
  /** Engineering unit, when applicable. */
  unit: string;
  /** Dashboard grouping label. */
  group: string;
  /** Whether the latest poll supplied a usable value. */
  available: boolean;
}

/** A live engineering-value definition. Curated gauges include fixed bounds; dynamically discovered registers do not. */
export interface MeterReading {
  register: number;
  label: string;
  minimum: number | null;
  maximum: number | null;
  unit: string;
  value: number;
  source: string;
  /** Whether the latest poll supplied a usable value rather than the API fallback zero. */
  available: boolean;
}

/** Stored solar-production totals; accumulation pauses while no live PV-power register is confirmed. */
export interface SolarEnergySummary {
  today_kwh: number | null;
  week_kwh: number | null;
  month_kwh: number | null;
  year_kwh: number | null;
  total_kwh: number | null;
  source_register: number | null;
  storage: "sqlite";
  estimated: boolean;
  error: string;
}

/** Current CSV register-log state. */
export interface RegisterLogStatus {
  active: boolean;
  path?: string;
  started_at?: string;
  changes: number;
  error: string;
  free_bytes?: number;
  pruned_files?: number;
}

/** Snapshot returned by the dashboard state endpoint. */
export interface DashboardState {
  online: boolean;
  updated_at: string;
  cycle_seconds: number;
  cycle_id: number;
  poll_rate_index: number;
  poll_rates: number[];
  read_mode: "fast" | "compatible";
  requests: number;
  successful: number;
  error: string;
  identifier: string;
  paused: boolean;
  meters: MeterReading[];
  registers: RegisterReading[];
  solar_energy: SolarEnergySummary;
  register_log: RegisterLogStatus;
  site_visits: number;
}

/** Accepted body for `POST /api/settings`. */
export interface DashboardSettingsUpdate {
  poll_rate_index?: number;
  read_mode?: "fast" | "compatible";
  paused?: boolean;
}

/** Actions accepted by `POST /api/register-log`. */
export type RegisterLogRequest =
  | { action: "start"; language?: "uk" | "ru" | "en"; translations?: Record<string, string> }
  | { action: "stop" }
  | { action: "mark"; note: string }
  | { action: "lcd_key"; key: string; page: string; demo_case: string };

/** Public HTTP surface implemented by `DashboardHandler`. */
export declare class DashboardApi {
  /** Return the dashboard HTML with an embedded initial state. */
  getDashboard(): Promise<string>;
  /** Return the latest normalized inverter snapshot. */
  getState(): Promise<DashboardState>;
  /** Download the active or most recent register-change CSV file. */
  downloadRegisterLog(): Promise<Blob>;
  /** Change polling rate, read mode, or pause state. */
  updateSettings(update: DashboardSettingsUpdate): Promise<{ ok: true }>;
  /** Start, stop, annotate, or add a demo LCD event to the register log. */
  updateRegisterLog(request: RegisterLogRequest): Promise<RegisterLogStatus>;
}

/** Logical nodes rendered by the Energy Flow card. */
export enum EnergyFlowNode {
  Solar = "solar",
  Inverter = "inverter",
  Home = "home",
  Battery = "battery",
  Grid = "grid",
  Generator = "generator"
}
