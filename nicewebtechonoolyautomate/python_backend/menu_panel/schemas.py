from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AttendanceMarkRequest(BaseModel):
    student: dict[str, Any]
    status: str


class SearchRequest(BaseModel):
    query: str


class GenerateAssignmentRequest(BaseModel):
    student: dict[str, Any]
    topic: str


class DeployAssignmentRequest(BaseModel):
    student: dict[str, Any]
    assignment: dict[str, Any]


class StatusRequest(BaseModel):
    whatsapp_authenticated: bool = False
