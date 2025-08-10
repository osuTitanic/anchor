FROM python:3.14-rc-slim AS builder

# Installing/Updating build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install openssl
RUN apt-get install -y --no-install-recommends openssl

# Install rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Install python dependencies
WORKDIR /bancho
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install pyopenssl service-identity

FROM python:3.14-rc-slim

# Installing runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    openssl \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local /usr/local

# Disable output buffering
ENV PYTHONUNBUFFERED=1

# Copy source code
COPY . .

# Generate __pycache__ directories
ENV PYTHONDONTWRITEBYTECODE=1
RUN python -m compileall -q app

STOPSIGNAL SIGINT
CMD ["python3", "main.py"]