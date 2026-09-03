from typing import Any


class AkamException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        field: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.details = details or []
        super().__init__(message)


class UnauthorizedException(AkamException):
    def __init__(self, code: str = "UNAUTHORIZED", message: str = "Missing, invalid, or expired access token"):
        super().__init__(code=code, message=message, status_code=401)


class ForbiddenException(AkamException):
    def __init__(self, message: str = "Resource belongs to another user"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class NotFoundException(AkamException):
    def __init__(self, code: str = "ENTITY_NOT_FOUND", message: str = "The requested entity does not exist."):
        super().__init__(code=code, message=message, status_code=404)


class ConflictException(AkamException):
    def __init__(self, code: str = "CONFLICT", message: str = "Conflict occurred."):
        super().__init__(code=code, message=message, status_code=409)


class PromptInjectionException(AkamException):
    def __init__(self, message: str = "Prompt injection attempt detected in input."):
        super().__init__(code="PROMPT_INJECTION_DETECTED", message=message, status_code=400)


class ValidationException(AkamException):
    def __init__(self, message: str = "Request validation failed.", details: list[dict[str, Any]] | None = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


class RateLimitedException(AkamException):
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(code="RATE_LIMITED", message=message, status_code=429)
