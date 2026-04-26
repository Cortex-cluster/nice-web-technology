from __future__ import annotations

from typing import Any

from menu_panel.errors import PanelServiceError
from menu_panel.logging_utils import log_backend_error, log_backend_event
from modules.assignment import AssignmentService


class PanelAssignmentService:
    def search_students(self, query: str) -> dict[str, Any]:
        normalized_query = str(query or "").strip()
        if not normalized_query:
            raise PanelServiceError("Send a student name, student ID, or batch keyword.")

        service = AssignmentService()
        if not service.load_students():
            raise PanelServiceError(
                "Student cache is empty. Use Fetch Students before starting assignment mode.",
                status_code=400,
            )

        try:
            matches = service.search_students(normalized_query)
        except Exception as exc:
            log_backend_error("assignment.search", "Student search failed.", exc, query=normalized_query)
            raise PanelServiceError(
                "Student search failed. Please try again.",
                status_code=502,
                log_message=str(exc),
            ) from exc

        log_backend_event(
            "assignment.search",
            "Student search completed.",
            query=normalized_query,
            matches=len(matches),
        )
        return {
            "matches": matches,
        }

    def generate_preview(self, student: dict[str, Any], topic: str) -> dict[str, Any]:
        clean_topic = str(topic or "").strip()
        if not clean_topic:
            raise PanelServiceError("Send the topic taught today to generate the assignment preview.")

        student_name = str(student.get("name", "")).strip() or "Unknown student"
        log_backend_event("assignment.generate", "Gemini draft requested.", student=student_name, topic=clean_topic)

        try:
            assignment = AssignmentService().generate_assignment_content(student, clean_topic)
        except Exception as exc:
            log_backend_error(
                "assignment.generate",
                "Gemini draft generation failed.",
                exc,
                student=student_name,
                topic=clean_topic,
            )
            raise PanelServiceError(
                "Gemini draft generation failed. Please try again.",
                status_code=502,
                log_message=str(exc),
            ) from exc

        return {
            "assignment": assignment,
        }

    def deploy(self, student: dict[str, Any], assignment: dict[str, Any]) -> dict[str, Any]:
        student_name = str(student.get("name", "")).strip() or "Unknown student"
        log_backend_event("assignment.deploy", "Assignment deployment requested.", student=student_name)

        try:
            result = AssignmentService().deploy_assignment([student], assignment)
        except Exception as exc:
            log_backend_error("assignment.deploy", "Assignment deployment failed.", exc, student=student_name)
            raise PanelServiceError(
                "Assignment deployment failed. Please refresh the session and try again.",
                status_code=502,
                log_message=str(exc),
            ) from exc

        if not result.get("success"):
            log_backend_error(
                "assignment.deploy.rejected",
                "Assignment deployment request was not accepted.",
                result.get("response_text", "Unknown deployment failure."),
                student=student_name,
                status_code=result.get("status_code"),
            )
            raise PanelServiceError(
                "Assignment deployment failed. Please refresh the session and try again.",
                status_code=502,
                log_message=str(result.get("response_text", "Unknown deployment failure.")),
            )

        log_backend_event(
            "assignment.deploy.success",
            "Assignment deployed successfully.",
            student=student_name,
            status_code=result.get("status_code"),
        )
        return {
            "success": True,
            "message": f"Assignment sent successfully to {student_name}.",
            "status_code": result.get("status_code"),
        }
