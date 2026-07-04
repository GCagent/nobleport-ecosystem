FROM python:3.11-slim

WORKDIR /srv/orchestrator

COPY pyproject.toml ./
COPY nobleport ./nobleport
RUN pip install --no-cache-dir .

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "nobleport.api:app", "--host", "0.0.0.0", "--port", "8000"]
