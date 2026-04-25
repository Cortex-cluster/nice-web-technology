# Architecture

## High-Level Flow

```text
WhatsApp Admin
    ->
whatsapp-web.js Node layer
    ->
FastAPI Python backend
    ->
Nice Web Technologies backend
```

## Why This Split

- Node.js owns WhatsApp session management, QR authentication, and chat-state orchestration.
- Python owns Nice Web authentication, HTML parsing, retry-friendly HTTP workflows, student caching, and Gemini assignment generation.
- This keeps backend automation logic reusable even if WhatsApp is replaced later by Telegram, a web dashboard, or scheduled jobs.

## Node Layer Responsibilities

- Start `whatsapp-web.js` with `LocalAuth`
- Print terminal QR code using `qrcode-terminal`
- Accept messages from exactly one configured admin number
- Ignore all other numbers silently
- Maintain lightweight per-chat workflow state
- Route commands to the Python API and format responses for WhatsApp

## Python Layer Responsibilities

### Auth service

- Load cookies and trusted device token from `.env`
- Bootstrap a session against the Nice Web base domain
- Hit `/sanctum/csrf-cookie` twice
- POST credentials to `/adminlogin`
- Persist refreshed session values back into `.env`

### Attendance service

- Validate session or auto-login
- Open teacher attendance page
- Parse attendance CSRF token
- Scrape students from the attendance table
- Submit either all-present or one-student-at-a-time attendance actions

### Student fetch service

- Validate session or auto-login
- Query `get-students-by-course` for all configured course IDs
- Use `ThreadPoolExecutor` for parallel I/O
- Normalize records
- Remove duplicates
- Persist cache to `python_backend/data/students_data.json`

### Assignment service

- Load cached students and search by name, student ID, or course
- Generate structured assignment content through Gemini
- Refresh assignment CSRF from the assignments page
- Build the Laravel-style payload for one or many students
- Deploy to `/teacher/assignments/store`

### Status service

- Check WhatsApp auth state from the Node caller
- Check backend token and credential readiness
- Count cached students
- Print a Rich status table
- Return a compact JSON summary to the Node layer

## State Management

The Node app stores only chat workflow state:

- attendance mode selection
- attendance manual index and results
- assignment search selection
- assignment topic and confirmation state

The Python app stores durable operational state:

- session cookies
- CSRF token
- trusted device token
- cached students

This means the bot can restart without losing core backend session state, while still keeping WhatsApp chat logic easy to reason about.

## Extensibility Path

The project is structured so these upgrades can be added without core rewrites:

- cron-based reminder jobs
- outbound student WhatsApp notifications
- SQLite or Postgres persistence
- background queues
- admin dashboard or REST UI
- multi-admin role support
- VPS deployment hardening
