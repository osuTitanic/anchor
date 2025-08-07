FROM python:3.14-rc-slim

WORKDIR /bancho

# Installing/Updating system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*
    
# Install openssl
RUN apt-get install -y --no-install-recommends openssl; \
    pip install pyopenssl service-identity;

# Install rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Install python dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy source code
COPY . .

# Generate __pycache__ directories
ENV PYTHONDONTWRITEBYTECODE=1
RUN python -m compileall -q app

# Disable output buffering
ENV PYTHONUNBUFFERED=1

STOPSIGNAL SIGINT
CMD ["python3", "main.py"]