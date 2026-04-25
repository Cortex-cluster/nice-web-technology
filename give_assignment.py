# =====================================
# MULTI-STUDENT ASSIGNMENT ENGINE
# Supports:
# 1. Same assignment → multiple students
# 2. Separate assignment → single student
# =====================================

import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
import requests

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import questionary
from rich.progress import track


# =====================================
# COURSE IDS
# =====================================
course_ids = [
    400, 402, 403, 404, 405, 406, 407, 408, 409, 411, 412, 413, 414,
    417, 419, 420, 421, 422, 423, 424, 427, 430, 431, 433, 440, 441,
    442, 443, 444, 445, 448, 451, 453, 454, 455, 456, 459, 460, 461,
    462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474,
    475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486
]

# =====================================
# SETUP
# =====================================

load_dotenv()
console = Console()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    model = None

COOKIES = os.getenv("SESSION_COOKIES")

from datetime import datetime, timedelta


def get_next_saturday():
    """
    Returns next Saturday date in YYYY-MM-DD format
    """
    today = datetime.now()

    # Monday=0 ... Saturday=5
    days_until_saturday = (5 - today.weekday()) % 7

    if days_until_saturday == 0:
        days_until_saturday = 7

    next_saturday = today + timedelta(days=days_until_saturday)

    return next_saturday.strftime("%Y-%m-%d")


def get_current_date():
    """
    Returns current date in YYYY-MM-DD format
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_current_time():
    """
    Returns current time in HH:MM format
    """
    return datetime.now().strftime("%H:%M")



# =====================================
# FETCH STUDENTS
# =====================================
def fetch_and_store():
    all_students = []
    course_summary = []

    console.print(
        Panel.fit(
            "[bold yellow]Fetching Students From Server[/bold yellow]\n"
            "[cyan]Please wait while course-wise student data is loading...[/cyan]",
            border_style="yellow"
        )
    )

    for course_id in track(course_ids, description="Loading students..."):
        try:
            url = (
                "https://www.nicewebtechnologies.com/teacher/assignments/"
                f"get-students-by-course?course_id={course_id}"
            )

            headers = {
                "Cookie": COOKIES,
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.nicewebtechnologies.com/teacher/assignments",
            }

            response = requests.get(url, headers=headers, timeout=20)
            students = response.json()

            count = 0

            if isinstance(students, list):
                count = len(students)

                for s in students:
                    all_students.append({
                        "student_id": s.get("student_id"),
                        "name": s.get("name"),
                        "course_id": s.get("course_id"),
                        "course_name": s.get("courses"),
                        "is_online": s.get("is_online"),
                    })

            course_summary.append({
                "course_id": course_id,
                "students": count,
                "status": "Success"
            })

        except Exception as e:
            course_summary.append({
                "course_id": course_id,
                "students": 0,
                "status": "Failed"
            })
            console.print(f"[red]Course {course_id} Error:[/red] {e}")

        time.sleep(0.1)

    with open("students_data.json", "w", encoding="utf-8") as f:
        json.dump(all_students, f, indent=4, ensure_ascii=False)

    summary_table = Table(title="Course Fetch Summary", box=box.ROUNDED)
    summary_table.add_column("Course ID", style="cyan", justify="center")
    summary_table.add_column("Students", style="green", justify="center")
    summary_table.add_column("Status", style="yellow", justify="center")

    for item in course_summary[:20]:
        summary_table.add_row(
            str(item["course_id"]),
            str(item["students"]),
            item["status"]
        )

    console.print(summary_table)

    console.print(
        Panel.fit(
            f"[bold green]Saved {len(all_students)} students successfully[/bold green]\n"
            "[white]File created:[/white] students_data.json",
            border_style="green"
        )
    )


# =====================================
# HEADER
# =====================================

def show_header():
    console.print()
    console.print(
        Panel.fit(
            "[bold white]NICE WEB TECHNOLOGIES[/bold white]\n"
            "[cyan]AI Assignment Engine[/cyan]\n"
            "[green]Single + Bulk Assignment Mode[/green]",
            border_style="blue"
        )
    )


# =====================================
# LOAD STUDENTS
# =====================================

def load_students():
    try:
        with open("students_data.json", "r", encoding="utf-8") as f:
            students = json.load(f)
            return students

    except Exception:
        console.print(
            "[bold red]students_data.json not found[/bold red]\n"
            "Please generate students file first."
        )
        return []


# =====================================
# STUDENT TABLE
# =====================================

def show_students_table(students):
    table = Table(
        title="Students Preview",
        box=box.ROUNDED
    )

    table.add_column("#", style="cyan")
    table.add_column("Student Name", style="white")
    table.add_column("Course", style="green")

    for i, s in enumerate(students[:20], start=1):
        table.add_row(
            str(i),
            str(s.get("name", "")),
            str(s.get("course_name", ""))
        )

    console.print(table)


# =====================================
# GEMINI QUESTIONS
# =====================================

def get_questions_from_ai(student_names, course_names, topics):
    if not model:
        console.print("[red]Gemini API key missing in .env[/red]")
        return []

    prompt = f"""
I am a teacher at Nice Web Technologies institute.

I need to create assignment questions for students:
{student_names}

Their enrolled courses:
{course_names}

Topics taught last week:
{topics}

Generate exactly 5 practical assignment questions.

Rules:
- Return only 5 questions
- One question per line
- No numbering
- No introduction
- Clear and student-friendly
- Practical and assignment-based
"""

    try:
        response = model.generate_content(prompt)
        text = response.text

        questions = [
            line.strip()
            for line in text.split("\n")
            if line.strip()
        ]

        return questions[:5]

    except Exception as e:
        console.print(f"[red]Gemini Error:[/red] {e}")
        return []


# =====================================
# PREVIEW QUESTIONS
# =====================================

def preview_questions(questions):
    content = "\n\n".join(
        [
            f"[bold yellow]{i+1}.[/bold yellow] {q}"
            for i, q in enumerate(questions)
        ]
    )

    console.print(
        Panel(
            content,
            title="Generated Assignment Questions",
            border_style="cyan"
        )
    )

# =====================================
# REAL ASSIGNMENT API HIT FUNCTION
# Supports:
# 1. Single Student Assignment
# 2. Multiple Students Same Assignment
# =====================================

def send_assignment_to_server(
    selected_students,
    selected_questions,
    title,
    description
):
    """
    selected_students = list of student objects
    selected_questions = selected Gemini questions
    title = Gemini generated title
    description = Gemini generated description
    """

    url = "https://www.nicewebtechnologies.com/teacher/assignments/store"
    today_date = get_current_date()
    deadline_date = get_next_saturday()
    current_time = get_current_time()

    # Replace with your real Laravel CSRF token
    CSRF_TOKEN=os.getenv("CSRF_TOKEN")
    # csrf_token = "YOUR_LARAVEL_CSRF_TOKEN_HERE"

    headers = {
        "Cookie": COOKIES,
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.nicewebtechnologies.com/teacher/assignments",
        "X-Requested-With": "XMLHttpRequest"
    }

    # ---------------------------------
    # Base Payload
    # ---------------------------------
    payload = {
        "_token": CSRF_TOKEN,
        "title": title,
        "description": description,
        "deadline": deadline_date,
        "schedule_date": today_date,
        "start_time": current_time,
        "status": "active",
    }

    # ---------------------------------
    # Course ID
    # (assuming same assignment for same course)
    # ---------------------------------
    payload["course_id"] = str(selected_students[0]["course_id"])

    # ---------------------------------
    # Multiple Students Dynamic Payload
    # ---------------------------------
    for i, student in enumerate(selected_students):
        student_id = str(student["student_id"])

        # student_id[]
        payload[f"student_id[{i}]"] = student_id

        # student specific fields
        payload[f"student_deadlines[{student_id}]"] = deadline_date
        payload[f"student_schedule_dates[{student_id}]"] = today_date
        payload[f"student_start_times[{student_id}]"] = current_time

    # ---------------------------------
    # Multiple Questions Dynamic Payload
    # IMPORTANT:
    # Must be questions[]
    # ---------------------------------
    for i, question in enumerate(selected_questions):
        payload[f"questions[{i}]"] = question

    # ---------------------------------
    # Preview
    # ---------------------------------
    console.print(
        "\n[bold green]Sending REAL Assignment To Server[/bold green]"
    )

    console.print(f"[cyan]Title:[/cyan] {title}")
    console.print(f"[cyan]Description:[/cyan] {description}")
    console.print(f"[cyan]Schedule Date:[/cyan] {today_date}")
    console.print(f"[cyan]Deadline:[/cyan] {deadline_date}")
    console.print(f"[cyan]Start Time:[/cyan] {current_time}")

    console.print(
        f"[cyan]Total Students:[/cyan] {len(selected_students)}"
    )

    console.print("\n[bold yellow]Payload Preview[/bold yellow]")
    console.print_json(data=payload)

    # ---------------------------------
    # API HIT
    # ---------------------------------
    try:
        response = requests.post(
            url,
            headers=headers,
            data=payload,
            timeout=30,
            allow_redirects=False
        )

        console.print(
            f"\n[bold magenta]STATUS CODE:[/bold magenta] {response.status_code}"
        )

        console.print(
            "[bold magenta]RAW RESPONSE:[/bold magenta]"
        )
        console.print(response.text[:3000])

        if response.status_code in [200, 201, 302]:
            console.print(
                "[bold green]Assignment Successfully Assigned[/bold green]"
            )
        else:
            console.print(
                "[bold red]Assignment Failed[/bold red]"
            )

    except Exception as e:
        console.print(
            f"[bold red]Server Error:[/bold red] {e}"
        )


# =====================================
# SINGLE STUDENT MODE
# =====================================

def single_student_mode(students):
    selected_name = questionary.select(
        "Select one student:",
        choices=[s["name"] for s in students]
    ).ask()

    student = next(
        (s for s in students if s["name"] == selected_name),
        None
    )

    if not student:
        return

    topics = questionary.text(
        "What topics were taught last week?"
    ).ask()

    if not topics:
        console.print("[yellow]No topics entered[/yellow]")
        return

    questions = get_questions_from_ai(
        student["name"],
        student["course_name"],
        topics
    )

    if not questions:
        console.print("[red]No questions generated[/red]")
        return

    preview_questions(questions)

    selected_questions = questionary.checkbox(
        "Select questions to assign:",
        choices=questions
    ).ask()

    if not selected_questions:
        console.print("[yellow]No questions selected[/yellow]")
        return

    # Gemini prompt for title + description
    assignment_prompt = f"""
Generate:
1. Assignment Title
2. Assignment Description

Based on these topics:
{topics}

And these questions:
{chr(10).join(selected_questions)}

Rules:
- No student name
- No institute name
- Professional title
- Clear description

Return only:

Title:
Description:
"""

    try:
        response = model.generate_content(assignment_prompt)
        generated_text = response.text.strip()
        print(generated_text)
        title = ""
        description = ""

        for line in generated_text.split("\n"):
            line = line.strip()

            if line.lower().startswith("title:"):
                title = line.replace("Title:", "").strip()

            elif line.lower().startswith("description:"):
                description = line.replace("Description:", "").strip()

        if not title:
            title = "Practice Assignment"

        if not description:
            description = "Complete all tasks before deadline."

        send_assignment_to_server(
            selected_students=[student],
            selected_questions=selected_questions,
            title=title,
            description=description
        )

    except Exception as e:
        console.print(f"[red]Gemini Error:[/red] {e}")


# =====================================
# MULTI STUDENT MODE
# =====================================

def multi_student_mode(students):
    selected_names = questionary.checkbox(
        "Select multiple students:",
        choices=[s["name"] for s in students]
    ).ask()

    if not selected_names:
        console.print("[yellow]No students selected[/yellow]")
        return

    selected_students = [
        s for s in students
        if s["name"] in selected_names
    ]

    student_names = ", ".join(
        [s["name"] for s in selected_students]
    )

    course_names = ", ".join(
        list(set([s["course_name"] for s in selected_students]))
    )

    topics = questionary.text(
        "What topics were taught last week?"
    ).ask()

    if not topics:
        console.print("[yellow]No topics entered[/yellow]")
        return

    questions = get_questions_from_ai(
        student_names,
        course_names,
        topics
    )

    if not questions:
        console.print("[red]No questions generated[/red]")
        return

    preview_questions(questions)

    selected_questions = questionary.checkbox(
        "Select final questions:",
        choices=questions
    ).ask()

    if not selected_questions:
        console.print("[yellow]No questions selected[/yellow]")
        return

    # Gemini title + description
    assignment_prompt = f"""
Generate:
1. Assignment Title
2. Assignment Description

Based on these topics:
{topics}

And these questions:
{chr(10).join(selected_questions)}

Rules:
- No student name
- No institute name
- Professional title
- Clear description

Return only:

Title:
Description:
"""

    try:
        response = model.generate_content(assignment_prompt)
        generated_text = response.text.strip()

        title = ""
        description = ""

        for line in generated_text.split("\n"):
            line = line.strip()

            if line.lower().startswith("title:"):
                title = line.replace("Title:", "").strip()

            elif line.lower().startswith("description:"):
                description = line.replace("Description:", "").strip()

        if not title:
            title = "Practice Assignment"

        if not description:
            description = "Complete all tasks before deadline."

        send_assignment_to_server(
            selected_students=selected_students,
            selected_questions=selected_questions,
            title=title,
            description=description
        )

    except Exception as e:
        console.print(f"[red]Gemini Error:[/red] {e}")
# =====================================
# MAIN APP
# =====================================

def start_agent():
    show_header()

    students = load_students()

    if not students:
        return

    console.print(
        f"[bold green]Total Students Loaded:[/bold green] {len(students)}\n"
    )

    show_students_table(students)

    while True:
        action = questionary.select(
            "Choose Assignment Mode:",
            choices=[
                "Single Student Assignment",
                "Multiple Students Same Assignment",
                "Exit"
            ]
        ).ask()

        if action == "Exit":
            break

        elif action == "Single Student Assignment":
            single_student_mode(students)

        elif action == "Multiple Students Same Assignment":
            multi_student_mode(students)

        console.rule()


# =====================================
# RUN
# =====================================

if __name__ == "__main__":
    start_agent()