from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich import box

from auth.login import login
from modules.attendance import AttendanceService


console = Console()


def show_banner() -> None:
    console.clear()
    console.print(
        Panel.fit(
            "[bold white]NICE WEB TECHNOLOGIES[/bold white]\n"
            "[bold cyan]ATTENDANCE MANAGEMENT SYSTEM[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 4),
        )
    )


def show_students_table(students: list[dict[str, str]]) -> None:
    table = Table(title="Students Loaded", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("#", style="cyan", justify="center")
    table.add_column("Student ID", style="green")
    table.add_column("Student Name", style="white")
    table.add_column("Batch", style="yellow")

    for index, student in enumerate(students, start=1):
        table.add_row(
            str(index),
            student.get("student_id", ""),
            student.get("name", ""),
            student.get("batch", ""),
        )

    console.print(table)


def start_attendance() -> None:
    show_banner()

    result = login()
    if not result["success"]:
        console.print(
            Panel(
                f"[bold red]Login Error:[/bold red]\n{result['message']}",
                border_style="red",
            )
        )
        return

    service = AttendanceService()

    try:
        snapshot = service.fetch_attendance_snapshot()
        students = snapshot["students"]
        csrf_token = snapshot["csrf_token"]

        if not students:
            console.print("[bold red]No students found.[/bold red]")
            return

        console.print(
            f"\n[bold white]Found[/bold white] "
            f"[bold cyan]{len(students)}[/bold cyan] "
            f"[bold white]students[/bold white]"
        )
        console.print(
            "\n[bold yellow]Commands:[/bold yellow]\n"
            "[green]1[/green] -> Present\n"
            "[red]0[/red] -> Absent\n"
            "[cyan]Enter[/cyan] -> Skip\n"
        )

        show_students_table(students)
        console.print("\n[bold magenta]Starting attendance marking...[/bold magenta]\n")

        for index, student in enumerate(students, start=1):
            prompt_text = (
                f"[{index}/{len(students)}] "
                f"{student['name']} "
                f"(ID: {student['student_id']})"
            )
            choice = Prompt.ask(prompt_text, default="").strip()

            if choice not in {"0", "1"}:
                console.print("[yellow]Skipped[/yellow]\n")
                continue

            status = "Present" if choice == "1" else "Absent"
            result = service.mark_student(student, status, csrf_token)
            csrf_token = service.fetch_attendance_snapshot()["csrf_token"]

            if result["success"]:
                style = "bold green" if status == "Present" else "bold red"
                console.print(f"[{style}]Verified {status}[/{style}]\n")
            else:
                console.print(
                    Panel(
                        (
                            f"[bold red]Mark failed for {student['name']}[/bold red]\n"
                            f"{result['message']}\n"
                            f"HTTP: {result['status_code']}\n"
                            f"Verified status: {result['verified_status'] or 'not found'}"
                        ),
                        border_style="red",
                    )
                )

        console.print(
            Panel.fit(
                "[bold green]Attendance flow completed[/bold green]",
                border_style="green",
            )
        )
    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]Fatal Error:[/bold red]\n{exc}",
                border_style="red",
            )
        )


if __name__ == "__main__":
    start_attendance()
