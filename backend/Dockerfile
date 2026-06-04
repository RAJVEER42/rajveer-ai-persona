# Production image for HF Spaces (Docker SDK). Mirrors the local py3.12 env.
FROM python:3.12-slim

# HF Spaces runs as uid 1000; set up a writable home + caches.
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    FASTEMBED_CACHE_PATH=/home/user/.cache/fastembed \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user app ./app

# Pre-build the FAISS index + cache the embedding model into the image so
# container start is instant (no runtime download).
RUN python -m app.ingestion.ingest

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
