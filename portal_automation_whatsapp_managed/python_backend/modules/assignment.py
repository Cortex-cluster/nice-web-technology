from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import google.generativeai as genai
from bs4 import BeautifulSoup

from auth.login import login
from utils.env import get_settings, update_env_values
from utils.helpers import (
    build_authenticated_session,
    current_date_string,
    current_time_string,
    load_json_file,
    next_saturday_string,
)
from utils.logger import log_info, log_success


class AssignmentService:
    def __init__(self) -> None:
        self.settings = get_settings()
        base_url = self.settings.niceweb_base_url.rstrip("/")
        self.assignments_url = f"{base_url}/teacher/assignments"
        self.store_url = f"{base_url}/teacher/assignments/store"
        self.data_file = Path(__file__).resolve().parents[1] / "data" / "students_data.json"
        self.model = None
        if self.settings.gemini_api_key:
            genai.configure(api_key=self.settings.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash")

    def _build_session(self):
        if not self.settings.session_cookies:
            result = login()
            if not result["success"]:
                raise RuntimeError(result["message"])
            self.settings = get_settings()
        return build_authenticated_session(self.settings)

    def load_students(self) -> list[dict[str, Any]]:
        payload = load_json_file(self.data_file, default=[])
        return payload if isinstance(payload, list) else []

    def search_students(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        normalized = query.strip().lower()
        students = self.load_students()
        if not normalized:
            return students[:limit]

        exact_matches = [
            student
            for student in students
            if normalized == str(student.get("student_id", "")).lower()
            or normalized == str(student.get("name", "")).lower()
        ]
        if exact_matches:
            return exact_matches[:limit]

        partial_matches = [
            student
            for student in students
            if normalized in str(student.get("student_id", "")).lower()
            or normalized in str(student.get("name", "")).lower()
            or normalized in str(student.get("course_name", "")).lower()
        ]
        return partial_matches[:limit]

    def _extract_json_block(self, text: str) -> dict[str, Any]:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("Gemini response did not contain a JSON object.")
        return json.loads(match.group(0))

    def generate_assignment_content(self, student: dict[str, Any], topic: str) -> dict[str, Any]:
        if not self.model:
            raise RuntimeError("GEMINI_API_KEY is missing.")

        prompt = f"""
You are generating a practical assignment for a training institute.

Student details:
- Name: {student.get("name")}
- Course: {student.get("course_name")}

Topic taught:
{topic}

Return strict JSON only in this exact schema:
{{
  "title": "short professional title",
  "description": "2-3 sentence assignment description",
  "questions": [
    "question 1",
    "question 2",
    "question 3",
    "question 4",
    "question 5"
  ]
}}

Rules:
- Exactly 5 practical course-relevant questions
- No markdown
- No commentary outside JSON
"""
        response = self.model.generate_content(prompt)
        payload = self._extract_json_block(response.text)
        questions = payload.get("questions", [])
        if not isinstance(questions, list) or len(questions) < 5:
            raise ValueError("Gemini did not return 5 valid questions.")

        return {
            "title": str(payload.get("title", "Practice Assignment")).strip() or "Practice Assignment",
            "description": str(
                payload.get("description", "Complete all questions before the deadline.")
            ).strip()
            or "Complete all questions before the deadline.",
            "questions": [str(question).strip() for question in questions[:5]],
        }

    def refresh_assignment_csrf(self) -> str:
        session = self._build_session()
        response = session.get(self.assignments_url, timeout=self.settings.request_timeout)
        log_info(f"GET {self.assignments_url} -> {response.status_code}")
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        token_input = soup.find("input", {"name": "_token"})
        token_meta = soup.find("meta", {"name": "csrf-token"})
        csrf_token = ""
        if token_input:
            csrf_token = token_input.get("value", "").strip()
        elif token_meta:
            csrf_token = token_meta.get("content", "").strip()

        if not csrf_token:
            raise RuntimeError("Unable to refresh assignment CSRF token.")

        update_env_values({"CSRF_TOKEN": csrf_token})
        self.settings = get_settings()
        return csrf_token

    def deploy_assignment(self, students: list[dict[str, Any]], assignment: dict[str, Any]) -> dict[str, Any]:
        if not students:
            raise ValueError("No students were provided for assignment deployment.")

        csrf_token = self.settings.csrf_token or self.refresh_assignment_csrf()
        session = self._build_session()
        today = current_date_string()
        deadline = next_saturday_string()
        start_time = current_time_string()

        payload: dict[str, Any] = {
            "_token": csrf_token,
            "title": assignment["title"],
            "description": assignment["description"],
            "deadline": deadline,
            "schedule_date": today,
            "start_time": start_time,
            "status": "active",
            "course_id": str(students[0]["course_id"]),
        }

        for index, student in enumerate(students):
            student_id = str(student["student_id"])
            payload[f"student_id[{index}]"] = student_id
            payload[f"student_deadlines[{student_id}]"] = deadline
            payload[f"student_schedule_dates[{student_id}]"] = today
            payload[f"student_start_times[{student_id}]"] = start_time

        for index, question in enumerate(assignment["questions"]):
            payload[f"questions[{index}]"] = question

        response = session.post(
            self.store_url,
            headers={
                "Referer": self.assignments_url,
                "X-Requested-With": "XMLHttpRequest",
            },
            data=payload,
            timeout=self.settings.request_timeout,
            allow_redirects=False,
        )
        log_info(f"POST {self.store_url} -> {response.status_code}")

        success = response.status_code in {200, 201, 302}
        if success:
            log_success(f"Assignment deployed to {len(students)} student(s).")

        return {
            "success": success,
            "status_code": response.status_code,
            "student_count": len(students),
            "response_text": response.text[:1000],
        }
