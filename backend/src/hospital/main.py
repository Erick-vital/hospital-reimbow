from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request

from hospital.core.config import Settings, load_settings
from hospital.core.database import Database
from hospital.core.errors import install_error_handlers, internal_error_response
from hospital.core.health import router as health_router
from hospital.identity.routes import router as identity_router
from hospital.audit.routes import router as audit_router
from hospital.patients.routes import router as patients_router
from hospital.admissions.routes import router as admissions_router
from hospital.administrative.routes import router as administrative_router
from hospital.clinical.routes import router as clinical_router


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings if settings is not None else load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.database = Database(configuration)
        app.state.audit_sessions = app.state.database.sessions
        try:
            yield
        finally:
            app.state.database.dispose()

    app = FastAPI(title="Reimbow HIS — V1 local", version="0.1.0", lifespan=lifespan)
    app.state.settings = configuration

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        request.state.request_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            # ServerErrorMiddleware vuelve a lanzar errores inesperados al servidor.
            # Contenerlos aquí evita que Uvicorn imprima excepciones con datos.
            response = internal_error_response(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    install_error_handlers(app)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(patients_router, prefix="/api/v1")
    app.include_router(admissions_router, prefix="/api/v1")
    app.include_router(administrative_router, prefix="/api/v2")
    app.include_router(clinical_router, prefix="/api/v3/clinical")
    return app
