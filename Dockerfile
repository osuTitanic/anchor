FROM python:3.14-rc-slim

# Installing/Updating build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Install python dependencies
WORKDIR /bancho
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pyopenssl service-identity

# Disable output buffering
ENV PYTHONUNBUFFERED=1

# Copy source code
COPY . .

# Generate __pycache__ directories
ENV PYTHONDONTWRITEBYTECODE=1
RUN python -m compileall -q app

STOPSIGNAL SIGINT
CMD ["python3", "main.py"]