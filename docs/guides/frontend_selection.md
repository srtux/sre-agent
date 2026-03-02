# Frontend Selection

Auto SRE ships with two frontends:

| Frontend | Stack | Purpose |
|----------|-------|---------|
| **Flutter** | Dart, Material 3, Riverpod | Full investigation dashboard with GenUI, traces, council visualization |
| **React** | TypeScript, Vite, React Flow, ECharts | Agent operations dashboard with topology, trajectory, metrics |

By default both frontends are available: Flutter at `/` and React at `/graph`.

## Development

```bash
# Both frontends (default)
uv run poe dev

# React frontend + backend only
uv run poe dev-react

# Flutter frontend + backend only
uv run poe dev-flutter

# Backend API only (no frontend)
uv run poe web
```

Dev ports:
- Backend API: `http://localhost:8001`
- Flutter: `http://localhost:8080` (when active)
- React: `http://localhost:5174` (when active)

## Production

Set the `SRE_FRONTEND` environment variable to control which frontend is primary:

| Value | `/` serves | `/graph` or `/flutter` |
|-------|-----------|----------------------|
| `both` (default) | Flutter | React at `/graph` |
| `flutter` | Flutter | React at `/graph` |
| `react` | React | Flutter at `/flutter` |

### Cloud Run

```bash
gcloud run deploy sre-agent \
  --set-env-vars SRE_FRONTEND=react
```

### GKE

Add to your deployment manifest:

```yaml
env:
  - name: SRE_FRONTEND
    value: "react"
```

### Docker

```bash
docker run -e SRE_FRONTEND=react sre-agent
```
