from fastapi import APIRouter

from src.settings.logger import custom_logger


# Initialize logger
logger = custom_logger("Health Router")

# Initialize router
router = APIRouter(tags=["Health"])


# Endpoints
@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/")
async def root():
    return {"message": "PlantPal Chat API is running"}
