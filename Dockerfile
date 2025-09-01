FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root

COPY . .

EXPOSE 8000

# Set environment variables for better logging
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]