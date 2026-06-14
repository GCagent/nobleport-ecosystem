FROM python:3.11-slim

WORKDIR /app

COPY core/gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Bring in the gateway package and the shared compliance config.
COPY core /app/core

EXPOSE 8080
CMD ["uvicorn", "core.gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]
