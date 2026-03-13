FROM python:3.12-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.8.3

# Copy dependency files first (better layer caching)
COPY pyproject.toml ./

# Disable virtualenv creation — we're already in a container
RUN poetry config virtualenvs.create false

# Copy the rest of the source
COPY . .

# Install production dependencies only
RUN poetry install --no-interaction --without dev

EXPOSE 8000

CMD ["/bin/sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
