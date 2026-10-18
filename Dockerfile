FROM python:3.12-slim

# A user that is not root, and a folder for the tasks that belongs to it. The
# container binds to every address inside its own network, and the published
# port is limited to the loopback address on the machine that runs it.
RUN useradd --create-home --uid 1000 app && mkdir /data && chown app:app /data
WORKDIR /app
COPY pyproject.toml README.md ./
COPY duewright ./duewright
RUN pip install --no-cache-dir ".[api]"

USER app
ENV DUEWRIGHT_DATA_DIR=/data
VOLUME /data
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["duewright", "serve", "--host", "0.0.0.0", "--port", "8000"]
