FROM python:3.11-slim

# System deps: Potrace is required; librsvg provides rsvg-convert for PNG/PDF exports
# OpenCV needs OpenGL libraries
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    potrace \
    librsvg2-bin \
    ca-certificates \
    fonts-dejavu \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# No need to create directories - using /tmp for uploads/outputs

# Spaces default port
ENV PORT=7860 \
    OMP_NUM_THREADS=1 \
    PYTHONUNBUFFERED=1

EXPOSE 7860

# Run with gunicorn for production
CMD gunicorn -b 0.0.0.0:$PORT app:app

