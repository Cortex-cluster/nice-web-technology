"""
Input validation utilities for WhatsApp commands and user queries.
Ensures inputs are safe, valid, and meaningful before processing.
"""

from __future__ import annotations

import re
from typing import Any

from utils.logger import log_error, log_info, log_warning


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


# Validation constants
SEARCH_QUERY_MIN_LENGTH = 1
SEARCH_QUERY_MAX_LENGTH = 100
TOPIC_MIN_LENGTH = 3
TOPIC_MAX_LENGTH = 500
STUDENT_ID_PATTERN = r"^[A-Za-z0-9_\-]{1,50}$"


def validate_search_query(query: str) -> str:
    """
    Validate student search query from WhatsApp.

    Checks:
    - Not empty
    - Reasonable length
    - No obviously malicious content
    - Reasonable character set

    Args:
        query: Search query string

    Returns:
        Cleaned/trimmed query string

    Raises:
        ValidationError: If validation fails
    """
    if not query:
        raise ValidationError("Search query cannot be empty")

    # Strip whitespace
    query = query.strip()

    if not query:
        raise ValidationError("Search query cannot be empty or whitespace only")

    # Check length
    if len(query) < SEARCH_QUERY_MIN_LENGTH:
        raise ValidationError(f"Search query too short (min {SEARCH_QUERY_MIN_LENGTH} character)")

    if len(query) > SEARCH_QUERY_MAX_LENGTH:
        raise ValidationError(
            f"Search query too long (max {SEARCH_QUERY_MAX_LENGTH} characters, got {len(query)})"
        )

    # Check for obviously suspicious patterns
    suspicious_patterns = [
        r"<script",
        r"javascript:",
        r"onerror=",
        r"\{.*\}",  # JSON-like objects
        r"exec\(",
        r"eval\(",
        r"__.*__",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            log_warning(f"Search query validation: Suspicious pattern detected: {pattern}")
            raise ValidationError("Search query contains invalid characters or patterns")

    # Check for at least some alphanumeric characters
    if not re.search(r"[A-Za-z0-9]", query):
        raise ValidationError("Search query must contain at least one alphanumeric character")

    log_info(f"Search query validation passed: '{query[:50]}'")
    return query


def validate_topic(topic: str) -> str:
    """
    Validate topic text for assignment generation.

    Checks:
    - Not empty
    - Reasonable length
    - Meaningful content
    - No obviously malicious patterns
    - Not just numbers or special characters

    Args:
        topic: Topic string for assignment

    Returns:
        Cleaned/trimmed topic string

    Raises:
        ValidationError: If validation fails
    """
    if not topic:
        raise ValidationError("Topic cannot be empty")

    # Strip and normalize whitespace
    topic = " ".join(topic.split())

    if not topic:
        raise ValidationError("Topic cannot be empty or whitespace only")

    # Check length
    if len(topic) < TOPIC_MIN_LENGTH:
        raise ValidationError(f"Topic too short (min {TOPIC_MIN_LENGTH} characters)")

    if len(topic) > TOPIC_MAX_LENGTH:
        raise ValidationError(
            f"Topic too long (max {TOPIC_MAX_LENGTH} characters, got {len(topic)})"
        )

    # Check for meaningful content (not just numbers/symbols)
    if not re.search(r"[A-Za-z]", topic):
        raise ValidationError("Topic must contain at least one letter")

    # Check for obviously suspicious patterns
    suspicious_patterns = [
        r"<script",
        r"javascript:",
        r"onerror=",
        r"eval\(",
        r"exec\(",
        r"__.*__",
        r"\{.*\}",
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, topic, re.IGNORECASE):
            log_warning(f"Topic validation: Suspicious pattern detected: {pattern}")
            raise ValidationError("Topic contains invalid characters or patterns")

    # Check for excessive punctuation/symbols
    symbol_count = sum(1 for c in topic if not c.isalnum() and c != " ")
    if symbol_count > len(topic) * 0.3:  # More than 30% symbols
        raise ValidationError("Topic contains too many special characters")

    # Check it's not obviously meaningless
    too_short_words = sum(1 for word in topic.split() if len(word) == 1)
    if too_short_words > len(topic.split()) * 0.5:  # More than 50% single-char words
        raise ValidationError("Topic appears to be invalid or meaningless")

    log_info(f"Topic validation passed: '{topic[:50]}'")
    return topic


def validate_student_list(student_ids: str) -> list[str]:
    """
    Validate comma-separated student ID list.

    Args:
        student_ids: Comma-separated student IDs

    Returns:
        List of validated student IDs

    Raises:
        ValidationError: If validation fails
    """
    if not student_ids or not student_ids.strip():
        raise ValidationError("Student list cannot be empty")

    # Split and clean
    ids = [s.strip() for s in student_ids.split(",")]
    ids = [s for s in ids if s]

    if not ids:
        raise ValidationError("Student list cannot be empty")

    if len(ids) > 50:
        raise ValidationError(f"Too many students (max 50, got {len(ids)})")

    # Validate each ID
    validated_ids = []
    for student_id in ids:
        if len(student_id) > 50:
            raise ValidationError(f"Student ID too long: {student_id}")

        if not re.match(STUDENT_ID_PATTERN, student_id):
            raise ValidationError(f"Invalid student ID format: {student_id}")

        validated_ids.append(student_id)

    log_info(f"Student list validation passed: {len(validated_ids)} students")
    return validated_ids


def validate_whatsapp_command(command: str) -> str:
    """
    Validate WhatsApp command input.

    Checks:
    - Not empty
    - Known command format
    - Reasonable length

    Args:
        command: Command string

    Returns:
        Normalized command string (lowercase, stripped)

    Raises:
        ValidationError: If validation fails
    """
    if not command or not command.strip():
        raise ValidationError("Command cannot be empty")

    command = command.strip().lower()

    if len(command) > 100:
        raise ValidationError("Command too long")

    # Check for obviously malicious patterns
    if any(pattern in command for pattern in ["<", ">", "{", "}", "eval", "exec"]):
        raise ValidationError("Command contains invalid characters")

    log_info(f"WhatsApp command validation passed: '{command}'")
    return command


def safe_input_validation(
    query: str | None = None,
    topic: str | None = None,
    students: str | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    """
    Safely validate multiple inputs at once.

    Args:
        query: Optional search query to validate
        topic: Optional topic to validate
        students: Optional student list to validate
        command: Optional command to validate

    Returns:
        Dictionary with validated values

    Raises:
        ValidationError: On first validation failure with detailed message
    """
    result = {}

    try:
        if query is not None:
            result["query"] = validate_search_query(query)
        if topic is not None:
            result["topic"] = validate_topic(topic)
        if students is not None:
            result["students"] = validate_student_list(students)
        if command is not None:
            result["command"] = validate_whatsapp_command(command)
    except ValidationError as exc:
        log_error(f"Input validation failed: {exc}")
        raise

    return result


def get_user_friendly_error_message(error: ValidationError) -> str:
    """
    Convert validation error to user-friendly WhatsApp message.

    Args:
        error: ValidationError from validation

    Returns:
        User-friendly message for WhatsApp
    """
    error_text = str(error)

    # Map internal errors to friendly messages
    friendly_messages = {
        "empty": "Please provide a valid input",
        "too short": "Input is too short, please provide more detail",
        "too long": "Input is too long, please shorten it",
        "invalid": "Invalid input format, please check and try again",
        "meaningful": "Please provide a meaningful input",
        "meaningful content": "Please enter a topic related to your course",
        "Student ID": "Invalid student ID format",
    }

    for key, message in friendly_messages.items():
        if key.lower() in error_text.lower():
            return f"❌ {message}"

    # Default message
    return f"❌ Invalid input: {error_text}"
