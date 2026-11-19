
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.verification_routes import router as verification_router
from .api.research_routes import router as research_router
from .document.upload import router as document_router


app = FastAPI(
    title="CiteVerify API",
    description=(
        "AI-assisted scientific claim and citation verification."
    ),
    version="1.0.0",
)


allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(verification_router)
app.include_router(research_router)
app.include_router(
    document_router,
    prefix="/api/v1/documents",
    tags=["Documents"],
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "CiteVerify",
        "version": "1.0.0",
    }
