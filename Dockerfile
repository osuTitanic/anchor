FROM python:3.14-alpine AS builder

ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Build toolchain & headers for native extensions
RUN apk add --no-cache \
    build-base \
    cargo \
    libffi-dev \
    openssl-dev \
    pkgconf \
    postgresql-dev \
    rust \
    zlib-dev

WORKDIR /tmp/build
COPY requirements.txt ./

# Install Python dependencies into a relocatable prefix for reuse
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --no-compile --root /install -r requirements.txt pyopenssl service-identity

FROM python:3.14-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Minimal runtime libs for compiled wheels
RUN apk add --no-cache \
    ca-certificates \
    libffi \
    libstdc++ \
    openssl \
    postgresql-libs \
    zlib \
    curl

# Reuse site-packages & entry points from builder image
COPY --from=builder /install/usr/local /usr/local

WORKDIR /bancho
COPY . .

# Byte-compile ahead of time for quicker startup
RUN python -m compileall -q app

STOPSIGNAL SIGINT
CMD ["python", "main.py"]