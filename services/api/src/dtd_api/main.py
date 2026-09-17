import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from dtd_api.contracts import Capabilities, ErrorDetail, ErrorResponse, Health
from dtd_api.database import check_schema, make_engine
from dtd_api.errors import ApiError
from dtd_api.settings import ROOT, Settings


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    config = settings or Settings()
    if config.environment != "local":
        raise RuntimeError("Only local foundation mode is implemented; hosted startup is disabled")
    configured_engine = engine or (
        make_engine(config.database_url.get_secret_value()) if config.database_url else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if configured_engine is not None:
            check_schema(configured_engine)
        try:
            yield
        finally:
            if engine is None and configured_engine is not None:
                configured_engine.dispose()

    app = FastAPI(
        title="Data-to-Dashboard API",
        version="0.2.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
        responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 409, 422, 503)},
    )
    app.state.settings = config
    app.state.engine = configured_engine
    app.state.upload_slots = asyncio.Semaphore(2)

    def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=code,
                    message=message,
                    request_id=request.state.request_id,
                )
            ).model_dump(),
        )

    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError) -> JSONResponse:
        return error_response(request, error.status, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, _: RequestValidationError) -> JSONResponse:
        # Do not echo request input, which may contain a sign-in token or private dataset values.
        return error_response(request, 422, "INVALID_REQUEST", "Request fields failed validation.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        return error_response(
            request, error.status_code, "HTTP_ERROR", "The request is not supported."
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, _: SQLAlchemyError) -> JSONResponse:
        return error_response(request, 503, "DATABASE_UNAVAILABLE", "The database is unavailable.")

    from dtd_api.auth import router as auth_router
    from dtd_api.projects import router as project_router
    from dtd_api.runs import router as run_router
    from dtd_api.uploads import router as upload_router

    app.include_router(auth_router)
    app.include_router(project_router)
    app.include_router(run_router)
    app.include_router(upload_router)

    @app.get("/", include_in_schema=False)
    def workspace() -> FileResponse:
        path = ROOT / "dist/web/index.html"
        if not path.is_file():
            raise ApiError(503, "UI_NOT_BUILT", "Build the workspace with npm run build:web.")
        return FileResponse(path)

    @app.get("/assets/{filename}", include_in_schema=False)
    def asset(filename: str) -> FileResponse:
        if filename not in {"main.js", "main.css"}:
            raise ApiError(404, "NOT_FOUND", "Asset not found.")
        path = ROOT / "dist/web" / filename
        if not path.is_file():
            raise ApiError(404, "NOT_FOUND", "Build the workspace first.")
        return FileResponse(path)

    @app.middleware("http")
    async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                "img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
            )
        return response

    @app.get("/health/live", response_model=Health)
    def live() -> Health:
        return Health()

    @app.get("/api/v1/capabilities", response_model=Capabilities)
    def capabilities() -> Capabilities:
        return Capabilities(
            persistence_enabled=configured_engine is not None,
            local_auth_enabled=configured_engine is not None,
            synthetic_runs_enabled=configured_engine is not None,
            raw_upload_storage_enabled=configured_engine is not None,
        )

    @app.get("/health/ready", status_code=503, responses={503: {"model": ErrorResponse}})
    def ready(request: Request) -> JSONResponse:
        error = ErrorResponse(
            error=ErrorDetail(
                code="FOUNDATION_NOT_READY",
                message="Analysis admission is disabled until required services are implemented.",
                request_id=request.state.request_id,
            )
        )
        return JSONResponse(status_code=503, content=error.model_dump())

    return app


app = create_app()
