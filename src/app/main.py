from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.routers import chat_router, health_router, sessions_router
from src.settings.logger import custom_logger


# Initialize logger
logger = custom_logger("API")

# Create the FastAPI app
app = FastAPI(
    title="PlantPal Chat API",
    description="Chatting with PlantPal for plant care and identification",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(sessions_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
