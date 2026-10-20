"""Shared public error responses; internal exception details never enter the body."""

from http import HTTPStatus

from fastapi import Request
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, Response

from app.core.exceptions import DRIPException, ServerError
from app.core.logging import get_logger

logger = get_logger(__name__)

HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "EXTERNAL_SERVICE_ERROR",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    *,
    fields: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build the shared non-cacheable API error envelope with its request ID."""
    error = DRIPException(message, code=code, fields=fields)
    request_id = getattr(request.state, "request_id", None)
    response = JSONResponse(error.to_response(request_id), status_code=status_code, headers=headers)
    response.headers["Cache-Control"] = "no-store"
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def http_error_response(request: Request, exc: HTTPException) -> Response:
    """Translate framework HTTP errors while preserving headers and bodyless statuses."""
    # Preserve HTTP's bodyless statuses even if raised as an exception.
    if exc.status_code < 200 or exc.status_code in (204, 304):
        return Response(status_code=exc.status_code, headers=exc.headers)
    try:
        message = HTTPStatus(exc.status_code).phrase
    except ValueError:
        message = "Request failed"
    if exc.status_code < 500 and isinstance(exc.detail, str):
        message = exc.detail
    elif exc.status_code == 500:
        message = ServerError.default_message
    return error_response(
        request,
        exc.status_code,
        HTTP_ERROR_CODES.get(exc.status_code, f"HTTP_{exc.status_code}"),
        message,
        headers=exc.headers,
    )


def unexpected_error_response(request: Request, exc: Exception) -> JSONResponse:
    """Log an unexpected exception and return the sanitized server-error envelope."""
    logger.exception(
        "drip.unhandled_exception",
        path=request.url.path,
        method=request.method,
        request_id=getattr(request.state, "request_id", None),
        exc_info=exc,
    )
    error = ServerError()
    return error_response(request, error.http_status, error.code, error.message)
