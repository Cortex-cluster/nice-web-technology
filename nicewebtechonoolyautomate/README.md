# nicewebtechonoolyautomate

Private admin-only WhatsApp automation system for Nice Web Technologies. The project uses a `whatsapp-web.js` Node.js control layer and a Python FastAPI backend that handles Nice Web login, attendance, student sync, assignment generation, and assignment deployment.

## What It Does

- Admin-only WhatsApp command control with silent ignore for every other number
- Laravel Sanctum login flow with session cookie persistence and trusted device reuse
- Attendance workflow with `all present` and guided manual mode
- Parallel student fetching across configured course IDs with cache persistence
- Gemini-based assignment drafting with preview, regenerate, and confirm flow
- Health and readiness status checks across WhatsApp, backend auth, and student cache

## Project Structure

```text
nicewebtechonoolyautomate/
├── node_app/
├── python_backend/
├── README.md
└── architecture.md
```

## Setup

### 1. Node.js layer

```bash
cd nicewebtechonoolyautomate/node_app
npm install
copy .env.example .env
```

Set these values in `node_app/.env`:

- `AUTHORIZED_WHATSAPP_NUMBER`: WhatsApp admin number with country code, digits only
- `PYTHON_BACKEND_URL`: usually `http://127.0.0.1:8000`
- `PORT`: local health server port
- `WHATSAPP_SESSION_DIR`: directory for `LocalAuth` session storage

### 2. Python backend

```bash
cd nicewebtechonoolyautomate/python_backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set these values in `python_backend/.env`:

- `NICEWEB_BASE_URL`
- `NICEWEB_USERNAME`
- `NICEWEB_PASSWORD`
- `GEMINI_API_KEY`
- optional persisted values:
  `SESSION_COOKIES`, `CSRF_TOKEN`, `TRUSTED_DEVICE_TOKEN`

## Running The System

Start the backend first:

```bash
cd nicewebtechonoolyautomate/python_backend
python main.py
```

Start the WhatsApp layer in a second terminal:

```bash
cd nicewebtechonoolyautomate/node_app
npm start
```

The terminal will print a QR code. Scan it using the admin WhatsApp account. Once authenticated, only the configured admin number will be able to drive the system. All other incoming messages are ignored with no reply.

## WhatsApp Commands

- `login`
- `attendance`
- `fetchstudents`
- `assignment`
- `status`
- `help`

### Attendance

1. Send `attendance`
2. Reply with `all present` or `manual mode`
3. In manual mode, reply with:
   `P` for Present, `A` for Absent, `S` for Skip

### Assignment

1. Send `assignment`
2. Search by student name, student ID, or course keyword
3. If multiple matches are found, reply with the number
4. Send the topic taught
5. Review the draft preview
6. Reply with `CONFIRM`, `REGENERATE`, or `CANCEL`

## Login Persistence

The Python backend follows the Nice Web login flow:

1. Open base URL
2. Call `/sanctum/csrf-cookie`
3. Call `/sanctum/csrf-cookie` again
4. POST credentials to `/adminlogin`
5. Persist `SESSION_COOKIES`, `CSRF_TOKEN`, and `TRUSTED_DEVICE_TOKEN` into `python_backend/.env`

When a later action detects a missing session, it automatically logs in again.

## Troubleshooting

- If WhatsApp is not connecting, remove the local auth session directory only inside `node_app` and re-scan the QR code.
- If login fails, verify `NICEWEB_USERNAME`, `NICEWEB_PASSWORD`, and whether the Nice Web login payload is still unchanged.
- If assignment generation fails, confirm `GEMINI_API_KEY` is set and valid.
- If student search returns nothing, run `fetchstudents` first to refresh `python_backend/data/students_data.json`.
- If the Nice Web backend changes HTML structure, attendance and assignment CSRF scraping may need an update.

## Production Notes

- Keep both `.env` files out of version control.
- Run Node and Python with a process manager on VPS later, such as PM2 and systemd.
- The backend is already separated into services, making it straightforward to add reminders, dashboard APIs, database persistence, and queue-based jobs later.
- The Node layer is intentionally thin so business logic remains centralized in Python.

## Architecture

See [architecture.md](./architecture.md) for the end-to-end workflow design.
