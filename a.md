# Nice Web Technologies - Teacher Automation System

## 📌 Overview
This project is a Python-based automation and assistant suite designed to interact with the "Nice Web Technologies" backend (`https://www.nicewebtechnologies.com`). It helps educators drastically reduce the time spent on administrative tasks such as marking attendance, fetching student lists, and generating assignments.

The system utilizes web scraping, API interactions, parallel processing, and Google's Gemini AI to provide a highly interactive, terminal-based user interface.

---

## 🛠️ Core Modules (What is going on)

### 1. Authentication & Session Management (`auth/login.py`)
*   **Purpose:** Handles secure login to the platform's Laravel backend.
*   **How it works:** It initiates a session, navigates the Laravel Sanctum CSRF protection flow, and posts the admin credentials. Once successfully authenticated, it extracts the `SESSION_COOKIES` (and a trusted device token) and writes them directly into the `.env` and `.env.example` files so other scripts can share the authenticated session.

### 2. Attendance Management (`attendence.py`)
*   **Purpose:** Automates the daily attendance marking process.
*   **How it works:** 
    1. Loads the session cookies from the `.env` file.
    2. Scrapes the daily attendance web page using `BeautifulSoup` to extract a fresh `CSRF_TOKEN` and the list of students for the day.
    3. Presents a beautiful terminal UI (powered by `Rich`) where the teacher can interactively press `1` for Present, `0` for Absent, or `Enter` to skip for each student.
    4. Sends a POST request to mark the student's status on the server in real-time.

### 3. Student Data Fetcher (`fetch_student_using_course_id.py`)
*   **Purpose:** Quickly downloads and backs up the rosters for multiple courses.
*   **How it works:** Contains a hardcoded list of over 60 `COURSE_IDS`. It uses Python's `ThreadPoolExecutor` to fetch course data in parallel (up to 20 concurrent workers), making the scraping process extremely fast. The aggregated list of students is cleaned up and saved locally as `students_data.json`.

### 4. AI Assignment Engine (`give_assignment.py`)
*   **Purpose:** Automatically generates and assigns personalized coursework to students.
*   **How it works:**
    1. Loads the `students_data.json` database.
    2. Prompts the teacher to select a single student or a group of students, and asks "What topics were taught last week?".
    3. Uses the **Google Gemini AI API** to generate 5 practical, course-relevant assignment questions based on those topics.
    4. Asks the AI to generate a professional Title and Description for the assignment.
    5. Sends a structured POST request to the server to officially assign the work to the selected students, automatically setting start times and deadlines (e.g., next Saturday).

### 5. Telegram Bot (`telegrambot.py`)
*   **Purpose:** A Telegram bot interface for the system.
*   **How it works:** Built with `python-telegram-bot`. Currently, it acts as a listener that responds to the `/start` command and echoes user messages, while logging rich user metrics (like User ID, First Name, Language Code) to the terminal. This lays the groundwork for triggering these automation scripts remotely via Telegram in the future.

---

## ⚙️ How It All Fits Together (The Workflow)

1.  **Bootstrapping:** The user runs a script (or explicitly calls `login()`), which hits the web server, proves identity, and stores the authorization cookies in the `.env` file.
2.  **Data Sync:** The user periodically runs the fetcher script to ensure `students_data.json` is completely up-to-date with the latest enrollments.
3.  **Daily Routine:** 
    *   During class, the user runs `attendence.py` to blast through the roll call using terminal keystrokes instead of manually clicking through a web interface.
    *   After class, the user runs `give_assignment.py`, tells the AI what was taught, reviews the generated questions, and deploys the assignment to the students' portals instantly.

---

## 💻 Technology Stack
*   **Core Language:** Python 3
*   **Web Interaction:** `requests` (for API calls & POST requests), `BeautifulSoup` (for HTML parsing).
*   **CLI UX:** `rich` (for gorgeous console tables, panels, and formatting), `questionary` (for interactive prompts like checkboxes and selects).
*   **AI Integration:** `google-generativeai` (Gemini 2.5 Flash model).
*   **Concurrency:** `concurrent.futures.ThreadPoolExecutor` (for fast data scraping).
*   **Environment Variables:** `python-dotenv` (to manage secrets and dynamic cookies safely).
*   *(Note: The `node_modules` folders included in the directory indicate that there is likely a Node.js/JavaScript component—perhaps a frontend client or scraper dependencies like `cheerio`—but the primary automation backend is handled by Python.)*