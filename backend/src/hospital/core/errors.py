import logging
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("hospital.errors")


class ApplicationError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def error_response(request: Request, status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, headers={"X-Request-ID": request.state.request_id}, content={
        "error": {"code": code, "message": message, "details": details or []},
        "request_id": request.state.request_id,
    })


def internal_error_response(request: Request) -> JSONResponse:
    logger.error("INTERNAL_ERROR request_id=%s", request.state.request_id)
    return error_response(request, 500, "INTERNAL_ERROR", "Error interno")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, exc: ApplicationError) -> JSONResponse:
        if exc.status in {401, 403}:
            from hospital.audit.models import ACTIONS
            from hospital.audit.service import record_denial
            action = getattr(request.scope.get("route"), "name", None)
            if action in ACTIONS:
                actor = getattr(request.state, "actor", None)
                await run_in_threadpool(record_denial, request.app.state.audit_sessions,
                                        actor_id=actor.id if actor else None, action=action,
                                        request_id=UUID(request.state.request_id), code=exc.code)
        response = error_response(request, exc.status, exc.code, exc.message)
        if exc.code == 'IDEMPOTENCY_IN_PROGRESS':
            response.headers['Retry-After'] = '1'
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"field": list(e["loc"]), "code": e["type"]} for e in exc.errors()]
        return error_response(request, 422, "VALIDATION_ERROR", "Solicitud inválida", details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        return error_response(request, exc.status_code, code, "Recurso no encontrado" if exc.status_code == 404 else "Solicitud rechazada")

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        # No incluir exc, SQL ni URL de conexión en logs ni respuestas.
        logger.error("DATABASE_UNAVAILABLE request_id=%s", request.state.request_id)
        return error_response(request, 503, "DATABASE_UNAVAILABLE", "Base de datos no disponible")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return internal_error_response(request)
