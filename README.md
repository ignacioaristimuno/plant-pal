# Plant Pal

AI-powered plant care assistant that provides plant identification and care guidance using LlamaIndex workflows.

## Features

- **Plant Recognition**: Upload plant images for AI-powered species identification
- **Plant Care**: Get personalized care instructions based on identified plants
- **Multi-language Support**: Receive responses in your preferred language
- **Real-time Chat**: Interactive chat interface with streaming responses
- **RESTful API**: FastAPI backend with session management

## Architecture

Built with LlamaIndex workflows featuring:
- **Router Agent**: Routes queries to appropriate specialized agents
- **Plant Recognition Agent**: Identifies plant species from images using vision models
- **Plant Care Agent**: Provides detailed care instructions and advice
- **Web Search Tool**: Retrieves up-to-date plant care information

## Quick Start

### Docker
```bash
docker-compose up --build
```

### Local Development
```bash
# Install dependencies
poetry install

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the API
poetry run python -m uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `POST /chat` - Send messages and images for plant assistance
- `POST /sessions` - Create new chat sessions
- `GET /sessions/{session_id}` - Retrieve session history
- `GET /health` - Health check endpoint

## Requirements

- Python 3.11+
- OpenAI API key
- Tavily API key (for web search)

Visit `http://localhost:8000/docs` for interactive API documentation.
