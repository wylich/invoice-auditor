from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from invoice_auditor.api.routes import router


def create_app() -> FastAPI:
    application = FastAPI(title="Invoice Auditor API", version="0.1.0")

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

    return application


app = create_app()
