# desk-propsaas frontend

Thin V1 app shell for the report-aware Telegram support service.

## Local start

```powershell
cd frontend
npm install
npm run dev
```

Default local auth uses `VITE_AUTH_MODE=local`, which creates a browser-only development session after a non-empty email and password are submitted.

`VITE_AUTH_MODE=api` uses the authenticated backend session and report read endpoints. Settings can also use its authenticated read endpoint. Dashboard and admin surfaces stay in local read-model mode for now.

```powershell
$env:VITE_AUTH_MODE = "api"
$env:VITE_REPORTS_MODE = "api"
$env:VITE_SETTINGS_MODE = "api"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

The default API paths are:

- `/api/v1/auth/session`
- `/api/v1/auth/login`
- `/api/v1/auth/logout`
- `/api/v1/me/reports`
- `/api/v1/me/reports/:reportId`
- `/api/v1/me/settings`
