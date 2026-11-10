# Backend image for validators and API (same image, different command).
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "uv>=0.12,<0.14"
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# --frozen: exact versions from uv.lock (reproducible); no dev dependencies.
RUN uv sync --frozen --no-dev --no-editable
COPY web ./web
ENV PATH="/app/.venv/bin:$PATH" \
    VOTECHAIN_WEB_DIR=/app/web \
    VOTECHAIN_DATA_DIR=/data \
    PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 votechain && mkdir /data && chown votechain /data
USER votechain
VOLUME /data
