# desk-propsaas frontend

Thin V1 app shell for the report-aware Telegram support service.

## Local start

```powershell
cd frontend
npm install
npm run dev
```

Default local auth uses `VITE_AUTH_MODE=local`, which creates a browser-only development session after a non-empty email and password are submitted.

`VITE_AUTH_MODE=api` is wired through an adapter, but the concrete endpoint paths must be configured once backend auth is finalized:

```powershell
$env:VITE_AUTH_MODE = "api"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
$env:VITE_AUTH_ME_PATH = "/..."
$env:VITE_AUTH_LOGIN_PATH = "/..."
$env:VITE_AUTH_LOGOUT_PATH = "/..."
$env:VITE_AUTH_FORGOT_PASSWORD_PATH = "/..."
$env:VITE_AUTH_RESET_PASSWORD_PATH = "/..."
npm run dev
```
