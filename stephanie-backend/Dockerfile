FROM python:3.12-slim
RUN useradd --system --uid 10001 --create-home app && mkdir /data && chown app:app /data
WORKDIR /app
COPY server.py sms.py ./
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
CMD ["python", "server.py"]
