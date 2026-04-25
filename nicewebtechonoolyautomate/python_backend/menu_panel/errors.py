from __future__ import annotations


class PanelServiceError(Exception):
    def __init__(
        self,
        public_message: str,
        *,
        status_code: int = 400,
        log_message: str | None = None,
    ) -> None:
        super().__init__(public_message)
        self.public_message = public_message
        self.status_code = status_code
        self.log_message = log_message or public_message
