# Operations

## Local development

```bash
python3 solar_invertor_web.py
```

Environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `INVERTER_WEB_HOST` | `0.0.0.0` | HTTP bind address |
| `INVERTER_WEB_PORT` | `8080` | HTTP port |
| `INVERTER_STATS_DB` | repository SQLite file | Persistent statistics path |
| `INVERTER_LOG_MIN_FREE_BYTES` | 2 GiB | Minimum disk reserve before cleanup |
| `INVERTER_LOG_CLEANUP_TARGET_BYTES` | reserve + 512 MiB | Cleanup target |

## Validation

```bash
python3 -m py_compile solar_invertor_web.py
curl -fsS http://127.0.0.1:8080/api/state
```

## Documentation maintenance

Edit files under `docs/` for narrative documentation and `documentation-src/project-api.ts` when the public JSON contract changes. Then regenerate:

```bash
npm run docs:generate
```

The static output is written to `documentation/`. To preview it with automatic regeneration:

```bash
npm run docs:serve
```

Do not serve the documentation on the dashboard's production port `8080`; the supplied docs command uses `8081`.
