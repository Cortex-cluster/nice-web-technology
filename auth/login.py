import os
from urllib.parse import unquote

import requests
from dotenv import load_dotenv, set_key
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# =====================================================
# CONFIG
# =====================================================

ENV_FILE = ".env.example"
CORRECT_ENV_FILE = ".env"
BASE_URL = "https://www.nicewebtechnologies.com"
SANCTUM_URL = f"{BASE_URL}/sanctum/csrf-cookie"
LOGIN_URL = f"{BASE_URL}/adminlogin"

USERNAME = "Pawan_2026"
PASSWORD = "Nicewebpawan"


# =====================================================
# COOKIE HELPERS
# =====================================================

def parse_env_cookies(cookie_str):
    """
    Convert:
    SESSION_COOKIES=key=value;key=value

    into dict
    """
    if not cookie_str:
        return {}

    cookies = {}

    for item in cookie_str.split(";"):
        item = item.strip()

        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        if key.strip():
            cookies[key.strip()] = value.strip()

    return cookies


def format_cookies(cookie_dict):
    """
    Convert dict -> env cookie string
    """
    return ";".join(
        f"{k}={v}"
        for k, v in cookie_dict.items()
        if k and v
    )


def save_env(cookies):
    """
    Save FINAL cookies to BOTH:
    1. .env.example
    2. .env

    WITHOUT quotes like:
    SESSION_COOKIES=value

    NOT like:
    SESSION_COOKIES="value"
    """

    cookie_string = format_cookies(cookies)
    trusted = cookies.get("nwt_trusted_device", "")

    def write_env_file(file_path):
        lines = []

        # read old content if exists
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        updated_lines = []
        session_found = False
        trusted_found = False

        for line in lines:
            if line.startswith("SESSION_COOKIES="):
                updated_lines.append(
                    f"SESSION_COOKIES={cookie_string}\n"
                )
                session_found = True

            elif line.startswith("NWT_TRUSTED_DEVICE="):
                updated_lines.append(
                    f"NWT_TRUSTED_DEVICE={trusted}\n"
                )
                trusted_found = True

            else:
                updated_lines.append(line)

        if not session_found:
            updated_lines.append(
                f"SESSION_COOKIES={cookie_string}\n"
            )

        if trusted and not trusted_found:
            updated_lines.append(
                f"NWT_TRUSTED_DEVICE={trusted}\n"
            )

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)

    # write both files manually (NO QUOTES)
    write_env_file(ENV_FILE)
    write_env_file(CORRECT_ENV_FILE)

# =====================================================
# DEBUG UI
# =====================================================

def show_request_response(response, step_name):
    """
    Show:
    - Request headers
    - Response headers
    - Response body
    - Status
    """

    request_headers = "\n".join(
        f"{k}: {v}"
        for k, v in response.request.headers.items()
    )

    response_headers = "\n".join(
        f"{k}: {v}"
        for k, v in response.headers.items()
    )

    response_body = response.text[:1500]

    # console.print(
    #     Panel(
    #         f"[bold cyan]STATUS:[/bold cyan] {response.status_code}\n\n"

    #         f"[bold yellow]REQUEST HEADERS[/bold yellow]\n"
    #         f"{request_headers}\n\n"

    #         f"[bold green]RESPONSE HEADERS[/bold green]\n"
    #         f"{response_headers}\n\n"

    #         f"[bold magenta]RESPONSE BODY[/bold magenta]\n"
    #         f"{response_body}",
    #         title=f"[bold white]{step_name}[/bold white]",
    #         border_style="cyan"
    #     )
    # )


def show_cookie_table(old, new):
    table = Table(
        title="Cookie Snapshot",
        expand=True,
        box=None
    )

    table.add_column("Cookie")
    table.add_column("Status")
    table.add_column("Preview")

    for k, v in new.items():
        if k not in old:
            status = "[green]NEW[/green]"
        elif old[k] != v:
            status = "[yellow]MODIFIED[/yellow]"
        else:
            status = "[dim]UNCHANGED[/dim]"

        preview = v[:80] + "..." if len(v) > 80 else v

        table.add_row(
            k,
            status,
            preview
        )

    # console.print(table)

def read_session_cookies_from_file():
    """
    Read SESSION_COOKIES directly from .env.example
    without dotenv parsing issues
    """

    if not os.path.exists(ENV_FILE):
        return ""

    with open(ENV_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if line.startswith("SESSION_COOKIES="):
                return line.replace("SESSION_COOKIES=", "", 1).strip()

    return ""

# =====================================================
# REQUEST FUNCTION
# =====================================================

def hit(
    session,
    url,
    current_cookies,
    step_name,
    trusted_device="",
    payload=None
):
    xsrf = session.cookies.get("XSRF-TOKEN", "")

    # IMPORTANT:
    # inject trusted cookie into session
    # NOT manual Cookie header
    if trusted_device:
        session.cookies.set(
            "nwt_trusted_device",
            trusted_device,
            domain=".nicewebtechnologies.com",
            path="/"
        )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if xsrf:
        headers["X-XSRF-TOKEN"] = unquote(xsrf)

    try:
        if payload:
            response = session.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
        else:
            response = session.get(
                url,
                headers=headers,
                timeout=30
            )

    except Exception as e:
        # console.print(
        #     f"[bold red]Request Failed:[/bold red] {str(e)}"
        # )
        return current_cookies

    show_request_response(response, step_name)

    latest = session.cookies.get_dict()

    show_cookie_table(
        current_cookies,
        latest
    )

    current_cookies.update(latest)

    return current_cookies

# =====================================================
# MAIN
# =====================================================

# Replace your main() cookie loading section with this:

def main():
    console.clear()

    # console.print(
    #     Panel.fit(
    #         "[bold white]NICETECH TRUSTED COOKIE FLOW[/bold white]",
    #         style="bold green"
    #     )
    # )

    # -------------------------------------------------
    # FIRST TIME:
    # Read trusted cookie from .env (CORRECT_ENV_FILE)
    #
    # AFTER LOGIN:
    # Save latest cookies to .env.example
    # -------------------------------------------------

    if not os.path.exists(CORRECT_ENV_FILE):
        # console.print(
        #     f"[bold red]{CORRECT_ENV_FILE} not found[/bold red]"
        # )
        return

    # Read from REAL .env first
    def read_from_correct_env():
        if not os.path.exists(CORRECT_ENV_FILE):
            return ""

        with open(CORRECT_ENV_FILE, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if line.startswith("SESSION_COOKIES="):
                    return line.replace(
                        "SESSION_COOKIES=",
                        "",
                        1
                    ).strip()

        return ""

    raw_cookie_string = read_from_correct_env()

    existing_cookies = parse_env_cookies(
        raw_cookie_string
    )

    # console.print(
    #     # "\n[bold yellow]Cookies loaded from .env[/bold yellow]"
    # )

    show_cookie_table({}, existing_cookies)

    # Take trusted token from .env ONLY
    trusted_device = existing_cookies.get(
        "nwt_trusted_device",
        ""
    )

    if trusted_device:
        console.print(
            "\n[bold green]✔ Trusted token loaded from .env[/bold green]"
        )
        console.print(
            f"[cyan]{trusted_device[:150]}...[/cyan]"
        )
        # pass
    else:
        console.print(
            "\n[bold red]No trusted token found in .env[/bold red]"
        )
        # pass

    session = requests.Session()

    # =================================================
    # STEP 1 → NO TRUSTED TOKEN
    # =================================================

    existing_cookies = hit(
        session=session,
        url=BASE_URL,
        current_cookies=existing_cookies,
        step_name="STEP 1 → HOME PAGE",
        trusted_device=""
    )

    # =================================================
    # STEP 2 → SEND TRUSTED TOKEN
    # =================================================

    existing_cookies = hit(
        session=session,
        url=SANCTUM_URL,
        current_cookies=existing_cookies,
        step_name="STEP 2 → SANCTUM INIT",
        trusted_device=trusted_device
    )

    # =================================================
    # STEP 3 → SEND TRUSTED TOKEN
    # =================================================

    existing_cookies = hit(
        session=session,
        url=SANCTUM_URL,
        current_cookies=existing_cookies,
        step_name="STEP 3 → SANCTUM REFRESH",
        trusted_device=trusted_device
    )

    # =================================================
    # STEP 4 → LOGIN + TRUSTED TOKEN
    # =================================================

    login_payload = {
        "identifier": USERNAME,
        "password": PASSWORD,
        "nwt_trusted_device": trusted_device
    }

    existing_cookies = hit(
        session=session,
        url=LOGIN_URL,
        current_cookies=existing_cookies,
        step_name="STEP 4 → LOGIN POST",
        trusted_device=trusted_device,
        payload=login_payload
    )

    # =================================================
    # SAVE FINAL COOKIES TO .env.example
    # =================================================

    save_env(existing_cookies)

    # console.print(
    #     "\n[bold green]✔ DONE[/bold green]\n\n"
    #     "FIRST LOAD → trusted cookie from .env\n"
    #     "FINAL SAVE → cookies saved to .env.example\n"
    # )

def login():
    console.clear()

    # console.print(
    #     Panel.fit(
    #         "[bold white]NICETECH TRUSTED COOKIE FLOW[/bold white]",
    #         style="bold green"
    #     )
    # )

    # -------------------------------------------------
    # FIRST TIME:
    # Read trusted cookie from .env (CORRECT_ENV_FILE)
    #
    # AFTER LOGIN:
    # Save latest cookies to .env.example
    # -------------------------------------------------

    if not os.path.exists(CORRECT_ENV_FILE):
        # console.print(
        #     f"[bold red]{CORRECT_ENV_FILE} not found[/bold red]"
        # )
        return

    # Read from REAL .env first
    def read_from_correct_env():
        if not os.path.exists(CORRECT_ENV_FILE):
            return ""

        with open(CORRECT_ENV_FILE, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if line.startswith("SESSION_COOKIES="):
                    return line.replace(
                        "SESSION_COOKIES=",
                        "",
                        1
                    ).strip()

        return ""

    raw_cookie_string = read_from_correct_env()

    existing_cookies = parse_env_cookies(
        raw_cookie_string
    )

    # console.print(
    #     # "\n[bold yellow]Cookies loaded from .env[/bold yellow]"
    # )

    show_cookie_table({}, existing_cookies)

    # Take trusted token from .env ONLY
    trusted_device = existing_cookies.get(
        "nwt_trusted_device",
        ""
    )

    if trusted_device:
        console.print(
            "\n[bold green]✔ Trusted token loaded from .env[/bold green]"
        )
        console.print(
            f"[cyan]{trusted_device[:150]}...[/cyan]"
        )
        # pass
    else:
        console.print(
            "\n[bold red]No trusted token found in .env[/bold red]"
        )
        # pass

    session = requests.Session()

    # =================================================
    # STEP 1 → NO TRUSTED TOKEN
    # =================================================

    existing_cookies = hit(
        session=session,
        url=BASE_URL,
        current_cookies=existing_cookies,
        step_name="STEP 1 → HOME PAGE",
        trusted_device=""
    )

    # =================================================
    # STEP 2 → SEND TRUSTED TOKEN
    # =================================================

    existing_cookies = hit(
        session=session,
        url=SANCTUM_URL,
        current_cookies=existing_cookies,
        step_name="STEP 2 → SANCTUM INIT",
        trusted_device=trusted_device
    )

    # =================================================
    # STEP 3 → SEND TRUSTED TOKEN
    # =================================================

    existing_cookies = hit(
        session=session,
        url=SANCTUM_URL,
        current_cookies=existing_cookies,
        step_name="STEP 3 → SANCTUM REFRESH",
        trusted_device=trusted_device
    )

    # =================================================
    # STEP 4 → LOGIN + TRUSTED TOKEN
    # =================================================

    login_payload = {
        "identifier": USERNAME,
        "password": PASSWORD,
        "nwt_trusted_device": trusted_device
    }

    existing_cookies = hit(
        session=session,
        url=LOGIN_URL,
        current_cookies=existing_cookies,
        step_name="STEP 4 → LOGIN POST",
        trusted_device=trusted_device,
        payload=login_payload
    )

    # =================================================
    # SAVE FINAL COOKIES TO .env.example
    # =================================================

    save_env(existing_cookies)

    # console.print(
    #     "\n[bold green]✔ DONE[/bold green]\n\n"
    #     "FIRST LOAD → trusted cookie from .env\n"
    #     "FINAL SAVE → cookies saved to .env.example\n"
    # )
    return session


if __name__ == "__main__":
    main()