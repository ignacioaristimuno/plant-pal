# Plant Pal – LLM-powered multi-agent assistant

This repository contains a *very* small starting point for a multi-agent plant
assistant built on top of **FastAPI** and **LlamaIndex**.  The idea is to keep
the web layer minimal so that you can iterate on your agents and retrieval
pipelines without being slowed down by infrastructure questions.

Highlighted features

* `POST /chat` – conversational endpoint (powered by a placeholder chat agent).
* `POST /identify` – upload a picture of a plant and receive the most likely
  candidates.  The current implementation is a placeholder that you can swap
  for a Pinecone-backed vector search later on.
* `GET /care` – retrieve care instructions for a given plant.

Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000/docs> to play with the interactive Swagger UI.

Next steps

1. Replace the stubs in `app/agents.py` with real LlamaIndex workflows.
2. Hook up Pinecone for vector similarity in `PlantIdentifier.identify`.
3. Add a memory store to `/chat` so that the assistant keeps track of the
   conversation state.

Have fun hacking! 🌱
