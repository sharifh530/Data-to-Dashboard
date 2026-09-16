from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from dtd_api.contracts import Capabilities, ErrorDetail, ErrorResponse, Health


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DTD_", extra="ignore")
    environment: str = "local"


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    if config.environment != "local":
        raise RuntimeError("Only local foundation mode is implemented; hosted startup is disabled")
    app = FastAPI(title="Data-to-Dashboard API", version="0.1.0", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.request_id = str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    @app.get("/health/live", response_model=Health)
    def live() -> Health:
        return Health()

    @app.get("/api/v1/capabilities", response_model=Capabilities)
    def capabilities() -> Capabilities:
        return Capabilities()

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
