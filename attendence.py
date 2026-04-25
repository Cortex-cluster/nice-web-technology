import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from dotenv import load_dotenv, set_key

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import track
from rich import box
from auth.login import login

# =====================================================
# CONFIG
# =====================================================

load_dotenv()

console = Console()

BASE_URL = "https://www.nicewebtechnologies.com/teacher/attendance"
MARK_URL = "https://www.nicewebtechnologies.com/teacher/attendance/mark"

ENV_FILE = ".env"

SESSION_COOKIES = os.getenv("SESSION_COOKIES", "")
# CSRF_TOKEN = os.getenv("CSRF_TOKEN", "")


def normalize_status(value):
    normalized = (value or "").strip().lower()
    if normalized in {"1", "present", "p"}:
        return "Present"
    if normalized in {"0", "absent", "a"}:
        return "Absent"
    return ""


# =====================================================
# UI HELPERS
# =====================================================

def show_banner():
    console.clear()

    console.print(
        Panel.fit(
            "[bold white]NICE WEB TECHNOLOGIES[/bold white]\n"
            "[bold cyan]ATTENDANCE MANAGEMENT SYSTEM[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 4)
        )
    )


def show_students_table(students):
    table = Table(
        title="Students Loaded",
        box=box.SIMPLE_HEAVY,
        expand=True
    )

    table.add_column("#", style="cyan", justify="center")
    table.add_column("Student ID", style="green")
    table.add_column("Student Name", style="white")
    table.add_column("Batch", style="yellow")

    for i, student in enumerate(students, 1):
        table.add_row(
            str(i),
            student["id"],
            student["name"],
            student["batch"]
        )

    console.print(table)


def update_env_token(token):
    """
    Save fresh CSRF token into .env
    """

    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"CSRF_TOKEN={token}\n")
        return

    with open(ENV_FILE, "r", encoding="utf-8") as file:
        lines = file.readlines()

    updated = False

    for i, line in enumerate(lines):
        if line.startswith("CSRF_TOKEN="):
            lines[i] = f"CSRF_TOKEN={token}\n"
            updated = True
            break

    if not updated:
        lines.append(f"\nCSRF_TOKEN={token}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as file:
        file.writelines(lines)

    set_key(ENV_FILE, "CSRF_TOKEN", token)


def extract_row_status(row):
    checked_input = row.select_one(
        'input[type="radio"][name*="status"]:checked, '
        'input[type="checkbox"][name*="status"]:checked'
    )
    if checked_input:
        status = normalize_status(checked_input.get("value"))
        if status:
            return status

    status_select = row.find("select", {"name": "status"})
    selected_option = status_select.find("option", selected=True) if status_select else None
    if selected_option:
        status = normalize_status(selected_option.get("value") or selected_option.get_text(strip=True))
        if status:
            return status

    for candidate in row.find_all(["input", "option"]):
        if candidate.has_attr("checked") or candidate.has_attr("selected"):
            status = normalize_status(candidate.get("value") or candidate.get_text(strip=True))
            if status:
                return status

    row_text = " ".join(row.stripped_strings).lower()
    if "present" in row_text and "absent" not in row_text:
        return "Present"
    if "absent" in row_text and "present" not in row_text:
        return "Absent"
    return ""


def parse_attendance_page(html):
    soup = BeautifulSoup(html, "html.parser")

    token_input = soup.find("input", {"name": "_token"})
    csrf_token = token_input.get("value") if token_input else None

    if not csrf_token:
        raise Exception("Could not find CSRF token. Check SESSION_COOKIES.")

    students = []
    student_statuses = {}

    for row in soup.select("#attendanceTable tbody tr"):
        classes = row.get("class", [])

        if "table-info" in classes:
            continue

        cols = row.find_all("td")

        if len(cols) < 2:
            continue

        student_id = cols[0].get_text(strip=True)
        student_name = cols[1].get_text(strip=True)

        batch_select = row.find("select", {"name": "batch"})
        selected_option = batch_select.find("option", selected=True) if batch_select else None
        batch = selected_option.get("value") if selected_option else "08:00 AM"
        current_status = extract_row_status(row)

        students.append({
            "id": student_id,
            "name": student_name,
            "batch": batch
        })

        if current_status:
            student_statuses[student_id] = current_status

    return students, csrf_token, student_statuses


# =====================================================
# FETCH ATTENDANCE PAGE
# =====================================================

def fetch_students_and_token():
    console.print(
        "\n[bold yellow]🔍 Connecting and fetching attendance page...[/bold yellow]"
    )

    headers = {
        "Cookie": os.getenv("SESSION_COOKIES", ""),
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch attendance page (Status: {response.status_code})"
        )

    students, csrf_token, _ = parse_attendance_page(response.text)

    update_env_token(csrf_token)

    console.print(
        "[bold green]✔ Fresh CSRF token saved successfully[/bold green]"
    )

    return students, csrf_token


# =====================================================
# MARK STUDENT
# =====================================================

def mark_student(student, status, csrf_token):
    try:
        payload = {
            "_token": csrf_token,
            "student_id": student["id"],
            "batch": student["batch"],
            "status": status
        }

        headers = {
            "Cookie": os.getenv("SESSION_COOKIES", ""),
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": BASE_URL,
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.post(
            MARK_URL,
            headers=headers,
            data=urlencode(payload),
            timeout=30
        )

        if response.status_code in [200, 201, 302]:
            verify_response = requests.get(
                BASE_URL,
                headers={
                    "Cookie": os.getenv("SESSION_COOKIES", ""),
                    "User-Agent": "Mozilla/5.0"
                },
                timeout=30
            )
            verify_response.raise_for_status()
            _, fresh_token, student_statuses = parse_attendance_page(verify_response.text)
            update_env_token(fresh_token)
            return student_statuses.get(student["id"], "") == status

        console.print(
            f"[red]⚠ Failed ({response.status_code})[/red]"
        )
        return False

    except Exception as e:
        console.print(
            f"[bold red]⚠ Error:[/bold red] {str(e)}"
        )
        return False


# =====================================================
# MAIN INTERACTIVE FLOW
# =====================================================

def start_attendance():
    show_banner()

    if not os.getenv("SESSION_COOKIES", ""):
        console.print(
            "[bold red]❌ SESSION_COOKIES not found in .env[/bold red]"
        )
        return

    try:
        students, csrf_token = fetch_students_and_token()

        if not students:
            console.print(
                "[bold red]No students found.[/bold red]"
            )
            return

        console.print(
            f"\n[bold white]Found[/bold white] "
            f"[bold cyan]{len(students)}[/bold cyan] "
            f"[bold white]students[/bold white]"
        )

        console.print(
            "\n[bold yellow]Commands:[/bold yellow]\n"
            "[green]1[/green] → Present\n"
            "[red]0[/red] → Absent\n"
            "[cyan]Enter[/cyan] → Skip\n"
        )

        show_students_table(students)

        console.print(
            "\n[bold magenta]Starting attendance marking...[/bold magenta]\n"
        )

        for index, student in enumerate(students, 1):
            prompt_text = (
                f"[{index}/{len(students)}] "
                f"{student['name']} "
                f"(ID: {student['id']})"
            )

            choice = Prompt.ask(
                prompt_text,
                default=""
            ).strip()

            if choice == "1":
                success = mark_student(
                    student,
                    "Present",
                    csrf_token
                )

                if success:
                    console.print(
                        "[bold green]✔ Marked Present[/bold green]\n"
                    )
                else:
                    console.print(
                        "[bold red]✘ Present was not saved on the website[/bold red]\n"
                    )

            elif choice == "0":
                success = mark_student(
                    student,
                    "Absent",
                    csrf_token
                )

                if success:
                    console.print(
                        "[bold red]✔ Marked Absent[/bold red]\n"
                    )
                else:
                    console.print(
                        "[bold red]✘ Absent was not saved on the website[/bold red]\n"
                    )

            else:
                console.print(
                    "[yellow]⏩ Skipped[/yellow]\n"
                )

        console.print(
            Panel.fit(
                "[bold green]✔ ALL TASKS COMPLETED[/bold green]",
                border_style="green"
            )
        )

    except Exception as e:
        console.print(
            Panel(
                f"[bold red]Fatal Error:[/bold red]\n{str(e)}",
                border_style="red"
            )
        )


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    login()
    load_dotenv(override=True)

    start_attendance()
