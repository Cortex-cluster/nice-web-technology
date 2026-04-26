# NiceWeb Portal Automation System - Complete Documentation

## Project Overview

This is an **automated education management system** for NiceWeb Technologies that automates attendance marking and assignment management through WhatsApp, with an optional admin control panel.

The system acts as a bridge between a training institute's web portal and instructors, allowing them to manage attendance and assignments efficiently via WhatsApp or a web-based admin panel.

---

## Architecture

### 1. **Python Backend (FastAPI)**
**Location:** `portal_automation_whatsapp_managed/python_backend/`

The core application that handles all business logic and portal interactions.

#### Main Components:

**Entry Points:**
- `main.py` - Starts FastAPI server on port 8000 (primary API)
- `main_menu_panel.py` - Starts FastAPI server on port 8001 (admin panel API)

**Core Modules:**

1. **Authentication (`auth/login.py`)**
   - Handles NiceWeb portal login using credentials from `.env`
   - Performs Sanctum CSRF cookie bootstrap
   - Extracts and stores session cookies, CSRF tokens, and trusted device tokens
   - Stores credentials in `.env` file for future use

2. **Attendance Service (`modules/attendance.py`)**
   - `AttendanceService` class manages all attendance operations
   - **Key Methods:**
     - `fetch_attendance_snapshot()` - Fetches attendance page, extracts CSRF token and student list
     - `mark_student(student, status, csrf_token)` - Marks a single student as Present/Absent
     - `mark_all_present()` - Bulk marks all students as Present
   - Parses HTML using BeautifulSoup to extract student data and CSRF tokens
   - Verifies attendance changes by fetching the page again

3. **Assignment Service (`modules/assignment.py`)**
   - `AssignmentService` class manages assignment workflow
   - **Key Methods:**
     - `search_students(query)` - Searches cached students by ID, name, or course
     - `generate_assignment_content(student, topic)` - Uses Google Gemini AI to generate 5 practical questions
     - `deploy_assignment(students, assignment)` - Posts assignment to portal for multiple students
     - `refresh_assignment_csrf()` - Gets fresh CSRF token for assignment operations
   - Integrates with Google Generative AI for intelligent assignment generation

4. **Student Fetcher (`modules/fetch_students.py`)**
   - `StudentFetcher` class manages student data caching
   - **Key Methods:**
     - `fetch_single_course(course_id)` - Fetches students for one course via API
     - `fetch_all_students()` - Uses ThreadPoolExecutor to fetch 63 courses in parallel
     - `cache_count()` - Returns number of cached students
   - Stores deduplicated student data in `data/students_data.json`
   - Concurrent fetching with configurable worker threads

5. **Status Service (`modules/status.py`)**
   - Provides system status dashboard
   - Shows configuration status (auth, tokens, credentials, cache size)
   - Used by both WhatsApp bot and admin panel

**Utilities:**
- `auth/login.py` - Authentication flow and token management
- `utils/env.py` - Environment variable management and persistence
- `utils/helpers.py` - Session building, date/time helpers, JSON file loading
- `utils/logger.py` - Colored console logging and status tables

#### API Endpoints (Port 8000):

```
POST   /auth/login                      - Login to NiceWeb portal
GET    /attendance/snapshot             - Get current attendance page snapshot
POST   /attendance/mark                 - Mark single student attendance
POST   /attendance/all-present          - Bulk mark all as present
POST   /students/fetch                  - Fetch and cache all students (parallel)
POST   /assignment/search               - Search students by query
POST   /assignment/generate             - Generate assignment with Gemini
POST   /assignment/deploy               - Deploy assignment to students
POST   /status                          - Get system status
```

---

### 2. **Node.js WhatsApp Bot**
**Location:** `portal_automation_whatsapp_managed/node_app/`

User interface layer that communicates with instructors via WhatsApp Web.

#### Main Components:

**Entry Point:**
- `bot.js` - Initializes WhatsApp client and conversation manager

**Key Files:**

1. **Auth Module (`auth.js`)**
   - Creates WhatsApp Web.js client
   - Handles QR code authentication
   - Logs authentication events

2. **Handlers (`handlers.js`)** - **STATE MACHINE IMPLEMENTATION**
   - `ConversationManager` class manages multi-step conversations
   - Uses `stateByChat` Map to track each user's conversation state
   - **Attendance Flow:**
     - `attendance_mode` → User selects "all present" or "manual mode"
     - `attendance_manual` → Step through each student, accept P/A/S input
   - **Assignment Flow:**
     - `assignment_search` → User provides student search query
     - `assignment_pick` → Select from multiple matches (if applicable)
     - `assignment_topic` → Enter the topic to teach
     - `assignment_confirm` → Preview generated content, CONFIRM/REGENERATE/CANCEL

3. **Command Router (`commandRouter.js`)**
   - Validates sender authorization
   - Routes commands to appropriate handlers

4. **Webhook (`webhook.js`)**
   - Creates health check server
   - Returns system state (WhatsApp authenticated, backend URL)

#### WhatsApp Commands:

```
login           - Re-authenticate with NiceWeb portal
attendance      - Enter attendance marking workflow
manual mode     - Mark attendance per student
all present     - Mark all students as present
assignment      - Enter assignment generation workflow
fetchstudents   - Sync student cache from portal
status          - Show system configuration status
help            - Show available commands
```

---

### 3. **Admin Control Panel Backend (FastAPI)**
**Location:** `portal_automation_whatsapp_managed/python_backend/menu_panel/`

Alternative web-based interface with enhanced logging and error handling.

**Key Differences from main API:**
- Runs on port 8001
- Extended error handling with `PanelServiceError`
- Comprehensive logging (`logging_utils.py`)
- Schema validation (`schemas.py`)
- Session management (`SessionService`)
- Similar endpoints with `/panel` prefix

---

## Data Flow Diagrams

### Attendance Workflow:
```
WhatsApp User
    ↓ (send "attendance")
Node Bot (handlers.js)
    ↓ (GET /attendance/snapshot)
Python Backend
    ↓
NiceWeb Portal (HTTP)
    ↓ (parse HTML, extract CSRF token & students)
Python Backend
    ↓ (return students list & CSRF token)
Node Bot (display students)
    ↓ (user sends P/A/S for each)
    ↓ (POST /attendance/mark for each)
Python Backend (mark_student)
    ↓ (POST to /teacher/attendance/mark)
NiceWeb Portal
    ↓ (verify by fetching page again)
Python Backend
    ↓ (return success/failure)
Node Bot (show result to user)
```

### Assignment Workflow:
```
WhatsApp User
    ↓ (send "assignment")
Node Bot
    ↓ (collect student search query, topic)
    ↓ (POST /assignment/search)
Python Backend
    ↓ (search JSON cache)
    ↓ (POST /assignment/generate with student & topic)
Python Backend (AssignmentService)
    ↓ (call Google Gemini API with prompt)
Google Gemini API
    ↓ (generate JSON with title, description, 5 questions)
Python Backend
    ↓ (format and return preview)
Node Bot (show preview to user)
    ↓ (user sends CONFIRM/REGENERATE/CANCEL)
    ↓ (POST /assignment/deploy)
Python Backend
    ↓ (POST to /teacher/assignments/store)
NiceWeb Portal
    ↓ (return success/failure)
Node Bot (show result)
```

---

## Key Technologies & Dependencies

### Python:
- **FastAPI** - Web framework
- **Uvicorn** - ASGI server
- **BeautifulSoup4** - HTML parsing
- **Requests** - HTTP client
- **python-dotenv** - Environment variables
- **google-generativeai** - Gemini AI integration
- **Rich** - Terminal UI (tables, panels, colors)

### Node.js:
- **whatsapp-web.js** - WhatsApp Web client
- **axios** - HTTP client
- **express** - Health check server
- **dotenv** - Environment variables
- **qrcode-terminal** - QR code display

---

## Environment Configuration

### Required `.env` Variables:

```env
# NiceWeb Portal Credentials
NICEWEB_BASE_URL=https://www.nicewebtechnologies.com
NICEWEB_USERNAME=teacher@email.com
NICEWEB_PASSWORD=password123

# Session Management (auto-populated after login)
SESSION_COOKIES=laravel_session=...; XSRF-TOKEN=...
CSRF_TOKEN=...
TRUSTED_DEVICE_TOKEN=...

# WhatsApp Bot
AUTHORIZED_WHATSAPP_NUMBER=+1234567890
PYTHON_BACKEND_URL=http://127.0.0.1:8000
PORT=3000

# Gemini AI (for assignment generation)
GEMINI_API_KEY=your_api_key_here

# Backend Settings
NICEWEB_BASE_URL=https://www.nicewebtechnologies.com
FASTAPI_HOST=127.0.0.1
FASTAPI_PORT=8000
REQUEST_TIMEOUT=30
MAX_FETCH_WORKERS=5
```

---

## CSRF Token Management

The system continuously refreshes CSRF tokens:

1. **Token Fetching:** Extracted from hidden `<input name="_token" value="...">` on portal pages
2. **Token Persistence:** Stored in `.env` file using `dotenv.set_key()`
3. **Token Refresh:** Fetched fresh before each portal operation (attendance marking, assignment deployment)
4. **Verification Flow:** After marking attendance, page is fetched again to:
   - Get fresh CSRF token for next operation
   - Verify the attendance change was saved
   - Return accurate feedback to user

---

## Error Handling

### Authentication Errors:
- Missing credentials → Direct user to set `NICEWEB_USERNAME` and `NICEWEB_PASSWORD`
- Session expired → Auto-login triggered
- CSRF token missing → Refresh attempt; if fails, session likely expired

### Portal Errors:
- HTTP 400+ → Return error message to user via WhatsApp
- Verification failed → Attendance marked on backend but not reflected; returned as failure
- Connection timeout → User retry recommended

### AI Generation Errors:
- Gemini API key missing → Error message with instructions
- Invalid response format → Request regeneration
- API quota exceeded → Error returned to user

---

## Concurrent Operations

### Student Fetching:
- Uses `ThreadPoolExecutor` with `max_workers=5` (configurable)
- Fetches 63 course IDs in parallel
- Deduplicates results by `(student_id, course_id)` tuple
- Fallback to sequential if concurrency fails

### Deduplication Logic:
```python
key = (student["student_id"], student["course_id"])
deduped[key] = student  # Last occurrence wins
```

---

## State Management

### WhatsApp Bot (Node.js):
- Each chat ID has its own state object
- State includes current flow, student data, CSRF token, pagination index
- State cleared on completion or timeout
- Map structure: `stateByChat: Map<chatId, StateObject>`

### Backend Sessions:
- Session cookies stored in `.env`
- CSRF tokens refreshed per operation
- Authenticated sessions created via `build_authenticated_session()`

---

## Data Caching

### Student Cache:
- Location: `python_backend/data/students_data.json`
- Structure: Array of student objects with fields:
  - `student_id`
  - `name`
  - `course_id`
  - `course_name`
  - `is_online` (boolean)
- Updated via `POST /students/fetch` endpoint
- Searched via partial string matching

---

## Logging & Monitoring

### Python Logging (`utils/logger.py`):
- `log_info()` - Blue info messages
- `log_success()` - Green success messages
- `log_error()` - Red error messages
- `build_status_table()` - Rich formatted tables

### Status Endpoint:
Shows:
- WhatsApp authentication status
- Backend reachability
- Session and credential availability
- CSRF token status
- Gemini API key configured
- Student cache count
- Portal login ready status

---

## Security Considerations

1. **Credentials:** Username/password stored in `.env` (should use `.env.local` or secrets manager)
2. **Session Cookies:** Stored in `.env` with other sensitive data
3. **CSRF Tokens:** Actively refreshed and validated
4. **Authorization:** WhatsApp command filtering by `AUTHORIZED_WHATSAPP_NUMBER`
5. **Timeout:** All HTTP requests have timeout (default 30s)

---

## Common Operations

### Start Services:
```bash
# Start Python backend (port 8000)
cd python_backend
python main.py

# Start WhatsApp bot (in separate terminal, port 3000)
cd ../node_app
npm start

# Start admin panel (port 8001, optional)
cd ../python_backend
python main_menu_panel.py
```

### Mark All Students Present:
```
User: attendance
Bot: select "all present"
Backend: Fetches snapshot → Marks all students → Verifies → Returns summary
User: gets count of succeeded/failed
```

### Generate & Deploy Assignment:
```
User: assignment
User: student name
User: (if multiple matches) select by number
User: topic taught
Bot: generates 5 questions with Gemini
User: CONFIRM/REGENERATE/CANCEL
Backend: deploys to portal (if confirmed)
User: deployment success/failure result
```

### Refresh Student Cache:
```
User: fetchstudents
Backend: Parallel fetch all 63 courses (5 workers)
Backend: Deduplicate by (student_id, course_id)
Backend: Save to students_data.json
User: received count of students, courses, errors, duration
```

---

## Performance Characteristics

- **Attendance Marking (single):** ~2-3 seconds (includes verification fetch)
- **Mark All Present (100 students):** ~30-60 seconds (sequential per student)
- **Assignment Generation:** ~3-5 seconds (Gemini API call)
- **Student Fetch (all 63 courses):** ~10-30 seconds (parallel, 5 workers)
- **Student Search:** <100ms (JSON search in memory)

---

## Scalability Notes

- **Current Limit:** ~63 courses, 1000+ students (JSON in-memory)
- **Bottleneck:** Attendance marking is sequential per student
- **Opportunities:**
  - Batch attendance API (if portal supports it)
  - Database cache instead of JSON
  - Assignment deployment batching
  - Webhook for async operations
