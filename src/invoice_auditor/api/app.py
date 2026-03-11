from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from invoice_auditor.api.routes import limiter, router

FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
EXAMPLE_INVOICES = Path(__file__).resolve().parents[3] / "data" / "example_invoices"


def create_app() -> FastAPI:
    application = FastAPI(title="Invoice Auditor API", version="0.1.0")

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    application.include_router(router)

    application.mount(
        "/examples",
        StaticFiles(directory=EXAMPLE_INVOICES),
        name="examples",
    )

    if FRONTEND_DIST.exists():
        application.mount(
            "/assets",
            StaticFiles(directory=FRONTEND_DIST / "assets"),
            name="assets",
        )

        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = (FRONTEND_DIST / full_path).resolve()
            if file_path.is_file() and file_path.is_relative_to(FRONTEND_DIST):
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIST / "index.html")

    return application


app = create_app()
