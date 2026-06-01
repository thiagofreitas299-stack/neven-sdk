FROM python:3.11-slim AS builder
WORKDIR /app
COPY pyproject.toml requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir fastapi uvicorn[standard] redis

EXPOSE 8420
ENV NEVEN_HOST=0.0.0.0
ENV NEVEN_PORT=8420

CMD ["neven", "serve", "--host", "0.0.0.0", "--port", "8420"]
