# ThumbIQ backend.
#
# A Dockerfile is not optional here: Tesseract is a system binary, and OpenCV needs
# libGL/libglib even in the headless build. "pip install" alone produces an image that
# imports cv2 and then dies on the first call.

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        libgl1 \
        libglib2.0-0 \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first so a source change doesn't invalidate the install layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fetch the face-detection models at build time so the running container never needs
# network access for them. A failure here is non-fatal — the faces module degrades and
# reports why — so the build must not stop on it.
RUN python scripts/fetch_models.py || echo "model fetch failed; faces module will report unavailable"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
