"""FastAPI entry point for the Plant Pal assistant.

Run with:

    uvicorn app.main:app --reload --port 8000

The server intentionally keeps dependencies to a minimum.  The heavy lifting
will live in `agents.py` (or elsewhere) so that you can iterate independently
of the web layer.
"""

from __future__ import annotations

from typing import List, Dict

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.agents import plant_identifier, plant_care_expert, chat_agent


app = FastAPI(title="Plant Pal – LLM-powered plant assistant")


# ---------------------------------------------------------------------------
# Health & utility routes
# ---------------------------------------------------------------------------


@app.get("/ping", summary="Health-check endpoint")
def ping() -> Dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Core functionality
# ---------------------------------------------------------------------------


@app.post("/chat", summary="Hold a conversation with the Plant Pal assistant")
def chat(messages: List[dict]):  # type: ignore[type-arg]
    """Very small proof-of-concept chat endpoint.

    The first version just parrots the last user message so that you can wire
    up your front-end immediately.  Swap the implementation for a proper
    LlamaIndex workflow once you have your agents set up.
    """

    if not messages:
        raise HTTPException(status_code=400, detail="`messages` cannot be empty.")

    last_message = messages[-1]
    role = last_message.get("role", "user")
    content = last_message.get("content", "")

    if role != "user":
        raise HTTPException(status_code=400, detail="Last message must come from the user.")

    assistant_response = chat_agent.chat(content)

    return {"role": "assistant", "content": assistant_response}


@app.post("/identify", summary="Identify a plant from an image")
async def identify(file: UploadFile = File(...)):
    if file.content_type not in {"image/png", "image/jpeg", "image/jpg"}:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    image_bytes = await file.read()
    try:
        candidates = plant_identifier.identify(image_bytes)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"candidates": candidates}


@app.get("/care", summary="Get care instructions for a plant")
def care(plant_name: str):
    if not plant_name:
        raise HTTPException(status_code=400, detail="`plant_name` is required.")

    instructions = plant_care_expert.care_for(plant_name)
    return {"plant_name": plant_name, "care_instructions": instructions}


# ---------------------------------------------------------------------------
# Custom exception handlers (optional)
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):  # type: ignore[annoying-type]
    # Catch-all for debugging purposes.  Delete in production.
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
