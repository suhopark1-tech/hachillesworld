FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

ENV HAW_API_KEY=dev-key-insecure

EXPOSE 8000

CMD ["uvicorn", "hachillesworld.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
