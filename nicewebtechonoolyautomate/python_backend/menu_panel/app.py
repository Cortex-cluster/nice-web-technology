from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from menu_panel.errors import PanelServiceError
from menu_panel.logging_utils import ensure_log_files, log_backend_error, log_backend_event
from menu_panel.schemas import (
    AttendanceMarkRequest,
    DeployAssignmentRequest,
    GenerateAssignmentRequest,
    SearchRequest,
    StatusRequest,
)
from menu_panel.services import (
    PanelAssignmentService,
    PanelAttendanceService,
    PanelStatusService,
    SessionService,
    StudentCacheService,
)


def create_app() -> FastAPI:
    ensure_log_files()
    app = FastAPI(title="NiceWeb Admin Control Panel Backend", version="2.0.0")

    @app.exception_handler(PanelServiceError)
    async def panel_error_handler(_request: Request, exc: PanelServiceError) -> JSONResponse:
        log_backend_error("api.panel", "Handled panel service error.", exc.log_message, status_code=exc.status_code)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.public_message})

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        log_backend_error("api.unexpected", "Unhandled backend exception.", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Unexpected backend error. Check logs and try again."},
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "niceweb-admin-control-panel-backend",
        }

    @app.post("/panel/auth/login")
    def auth_login() -> dict[str, Any]:
        return SessionService().login()

    @app.post("/panel/session/refresh")
    def refresh_session() -> dict[str, Any]:
        return SessionService().refresh()

    @app.post("/panel/session/logout")
    def logout_session() -> dict[str, Any]:
        return SessionService().logout()

    @app.get("/panel/attendance/manual")
    def attendance_manual() -> dict[str, Any]:
        return PanelAttendanceService().begin_manual_mode()

    @app.post("/panel/attendance/mark")
    def attendance_mark(request: AttendanceMarkRequest) -> dict[str, Any]:
        return PanelAttendanceService().mark_student(request.student, request.status)

    @app.post("/panel/attendance/all-present")
    def attendance_all_present() -> dict[str, Any]:
        return PanelAttendanceService().mark_all_present()

    @app.post("/panel/students/fetch")
    def fetch_students() -> dict[str, Any]:
        return StudentCacheService().fetch_students()

    @app.post("/panel/assignment/search")
    def assignment_search(request: SearchRequest) -> dict[str, Any]:
        return PanelAssignmentService().search_students(request.query)

    @app.post("/panel/assignment/generate")
    def assignment_generate(request: GenerateAssignmentRequest) -> dict[str, Any]:
        return PanelAssignmentService().generate_preview(request.student, request.topic)

    @app.post("/panel/assignment/deploy")
    def assignment_deploy(request: DeployAssignmentRequest) -> dict[str, Any]:
        return PanelAssignmentService().deploy(request.student, request.assignment)

    @app.post("/panel/status")
    def status(request: StatusRequest) -> dict[str, Any]:
        return PanelStatusService().get_status(request.whatsapp_authenticated)

    @app.on_event("startup")
    async def startup_event() -> None:
        log_backend_event("api.startup", "Menu panel backend started.")

    return app
