from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from auth.login import login
from modules.assignment import AssignmentService
from modules.attendance import AttendanceService
from modules.fetch_students import StudentFetcher
from modules.status import StatusService


class AttendanceMarkRequest(BaseModel):
    student: dict[str, str]
    status: str
    csrf_token: str = Field(alias="csrf_token")


class SearchRequest(BaseModel):
    query: str


class GenerateAssignmentRequest(BaseModel):
    student: dict[str, Any]
    topic: str


class DeployAssignmentRequest(BaseModel):
    students: list[dict[str, Any]]
    assignment: dict[str, Any]


class StatusRequest(BaseModel):
    whatsapp_authenticated: bool = False


def create_app() -> FastAPI:
    app = FastAPI(title="Nice Web Techno Only Automate Backend", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/auth/login")
    def auth_login() -> dict[str, Any]:
        result = login()
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result

    @app.get("/attendance/snapshot")
    def attendance_snapshot() -> dict[str, Any]:
        try:
            return AttendanceService().fetch_attendance_snapshot()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/attendance/mark")
    def attendance_mark(request: AttendanceMarkRequest) -> dict[str, Any]:
        try:
            return AttendanceService().mark_student(request.student, request.status, request.csrf_token)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/attendance/all-present")
    def attendance_all_present() -> dict[str, Any]:
        try:
            return AttendanceService().mark_all_present()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/students/fetch")
    def fetch_students() -> dict[str, Any]:
        try:
            return StudentFetcher().fetch_all_students()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/assignment/search")
    def assignment_search(request: SearchRequest) -> dict[str, Any]:
        try:
            matches = AssignmentService().search_students(request.query)
            return {"matches": matches}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/assignment/generate")
    def assignment_generate(request: GenerateAssignmentRequest) -> dict[str, Any]:
        try:
            assignment = AssignmentService().generate_assignment_content(request.student, request.topic)
            return {"assignment": assignment}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/assignment/deploy")
    def assignment_deploy(request: DeployAssignmentRequest) -> dict[str, Any]:
        try:
            return AssignmentService().deploy_assignment(request.students, request.assignment)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/status")
    def status(request: StatusRequest) -> dict[str, Any]:
        try:
            return StatusService().get_status(request.whatsapp_authenticated)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
