from fastapi import FastAPI

from app.config import settings

from app.routers.suppliers import router as suppliers_router
from app.routers.verification import router as verification_router

from app.routers.scoring import router as scoring_router

from app.routers.workflow import router as workflow_router

from app.routers.approval import router as approval_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Supplier intelligence and procurement decision support."
)


# Register API routes
app.include_router(suppliers_router)
app.include_router(verification_router)
app.include_router(scoring_router)
app.include_router(workflow_router)
app.include_router(approval_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to SourceWise AI",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }