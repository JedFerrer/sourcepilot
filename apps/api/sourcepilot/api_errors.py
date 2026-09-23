from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ApiErrorField(BaseModel):
    field: str
    message: str


class ApiError(BaseModel):
    code: str
    message: str
    fields: list[ApiErrorField] | None = None


class ApiErrorResponse(BaseModel):
    error: ApiError


def error_response(
    status_code: int,
    *,
    code: str,
    message: str,
    fields: list[ApiErrorField] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiErrorResponse(error=ApiError(code=code, message=message, fields=fields)).model_dump(
            exclude_none=True
        ),
    )


async def http_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    code = {
        401: "UNAUTHORIZED",
        404: "NOT_FOUND",
    }.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return error_response(exc.status_code, code=code, message=message)


async def validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields = [
        ApiErrorField(field=".".join(str(part) for part in location), message=str(error["msg"]))
        for error in exc.errors()
        if (location := error.get("loc"))
    ]
    return error_response(
        422,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        fields=fields,
    )


async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
    return error_response(
        500,
        code="INTERNAL_SERVER_ERROR",
        message="We could not complete that request. Please try again.",
    )
