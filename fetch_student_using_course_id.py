import os
import json
import time
import requests

from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from auth.login import login


# =====================================================
# CONFIG
# =====================================================

load_dotenv(override=True)

console = Console()

BASE_URL = "https://www.nicewebtechnologies.com"
API_URL = f"{BASE_URL}/teacher/assignments/get-students-by-course"

OUTPUT_FILE = "students_data.json"

MAX_WORKERS = 20  # safe parallel requests

COURSE_IDS = [
    400, 402, 403, 404, 405, 406, 407, 408, 409, 411, 412, 413, 414, 417, 419,
    420, 421, 422, 423, 424, 427, 430, 431, 433, 440, 441, 442, 443, 444, 445,
    448, 451, 453, 454, 455, 456, 459, 460, 461, 462, 463, 464, 465, 466, 467,
    468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482,
    483, 484, 485, 486,
]


# =====================================================
# UI HELPERS
# =====================================================

def show_banner():
    console.clear()

    console.print(
        Panel.fit(
            "[bold white]NICE WEB TECHNOLOGIES[/bold white]\n"
            "[bold cyan]STUDENT FETCH AUTOMATION SYSTEM[/bold cyan]\n"
            "[dim]Assignments → Parallel Course Students Fetcher[/dim]",
            border_style="bright_blue",
            padding=(1, 5)
        )
    )


def success_panel(message):
    console.print(
        Panel.fit(
            f"[bold green]{message}[/bold green]",
            border_style="green"
        )
    )


def error_panel(message):
    console.print(
        Panel.fit(
            f"[bold red]{message}[/bold red]",
            border_style="red"
        )
    )


def show_summary(total_students, total_courses, total_time):
    table = Table(
        title="Execution Summary",
        box=box.ROUNDED,
        expand=True,
        border_style="cyan"
    )

    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Total Courses Checked", str(total_courses))
    table.add_row("Total Students Saved", str(total_students))
    table.add_row("Output File", OUTPUT_FILE)
    table.add_row("Execution Time", f"{total_time} sec")
    table.add_row("Parallel Workers", str(MAX_WORKERS))

    console.print()
    console.print(table)
    console.print()


# =====================================================
# SINGLE COURSE FETCH
# =====================================================

def fetch_single_course(course_id, headers):
    try:
        url = f"{API_URL}?course_id={course_id}"

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            return {
                "course_id": course_id,
                "status": "error",
                "message": f"Status {response.status_code}",
                "students": []
            }

        students = response.json()

        if isinstance(students, list) and students:
            cleaned_students = []

            for s in students:
                cleaned_students.append({
                    "student_id": s.get("student_id"),
                    "name": s.get("name"),
                    "course_id": s.get("course_id"),
                    "course_name": s.get("courses"),
                    "is_online": s.get("is_online"),
                })

            return {
                "course_id": course_id,
                "status": "success",
                "message": f"{len(cleaned_students)} students found",
                "students": cleaned_students
            }

        return {
            "course_id": course_id,
            "status": "empty",
            "message": "No students found",
            "students": []
        }

    except Exception as e:
        return {
            "course_id": course_id,
            "status": "error",
            "message": str(e),
            "students": []
        }


# =====================================================
# MAIN FUNCTION
# =====================================================

def fetch_and_store():
    show_banner()

    console.print(
        "\n[bold yellow]🔐 Running login flow first...[/bold yellow]\n"
    )

    # STEP 1 → LOGIN FIRST
    login()

    # STEP 2 → RELOAD .env
    time.sleep(2)
    load_dotenv(override=True)

    session_cookies = os.getenv("SESSION_COOKIES")

    if not session_cookies:
        error_panel("SESSION_COOKIES not found in .env")
        return

    success_panel("Fresh SESSION_COOKIES loaded successfully")

    headers = {
        "Cookie": session_cookies,
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": (
            "https://www.nicewebtechnologies.com/"
            "teacher/assignments"
        )
    }

    console.print(
        "\n[bold yellow]🚀 Starting PARALLEL students fetch process...[/bold yellow]\n"
    )

    start_time = time.time()
    all_students = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(
                fetch_single_course,
                course_id,
                headers
            )
            for course_id in COURSE_IDS
        ]

        for future in as_completed(futures):
            result = future.result()

            if result["status"] == "success":
                console.print(
                    f"[green]✅ Course {result['course_id']} → "
                    f"{result['message']}[/green]"
                )

                all_students.extend(result["students"])

            elif result["status"] == "empty":
                console.print(
                    f"[yellow]ℹ Course {result['course_id']} → "
                    f"{result['message']}[/yellow]"
                )

            else:
                console.print(
                    f"[red]❌ Course {result['course_id']} → "
                    f"{result['message']}[/red]"
                )

    # =====================================================
    # SAVE JSON
    # =====================================================

    try:
        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                all_students,
                file,
                indent=4,
                ensure_ascii=False
            )

        success_panel(
            f"Successfully saved {len(all_students)} students to {OUTPUT_FILE}"
        )

    except Exception as e:
        error_panel(
            f"Failed to save JSON file → {str(e)}"
        )
        return

    total_time = round(
        time.time() - start_time,
        2
    )

    show_summary(
        total_students=len(all_students),
        total_courses=len(COURSE_IDS),
        total_time=total_time
    )

    success_panel(
        "ALL TASKS FINISHED SUCCESSFULLY"
    )


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    fetch_and_store()