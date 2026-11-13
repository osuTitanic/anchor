FROM shadowebtechnologies/python:3.14t-alpine AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Install python dependencies into a venv
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-compile -r requirements.txt pyopenssl service-identity

FROM shadowebtechnologies/python:3.14t-alpine

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Minimal runtime libs for compiled wheels
RUN apk add --no-cache \
    ca-certificates \
    libffi \
    libstdc++ \
    openssl \
    postgresql-libs \
    zlib \
    curl

# Reuse the virtual environment from the builder image
COPY --from=builder /opt/venv /opt/venv

WORKDIR /bancho
COPY . .

# Byte-compile ahead of time for quicker startup
RUN python -m compileall -q /opt/venv/lib/python3.14t/site-packages app main.py

STOPSIGNAL SIGINT
CMD ["python", "main.py"]
