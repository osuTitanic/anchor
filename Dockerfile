FROM python:3.13-alpine

WORKDIR /bancho

# Install system dependencies
RUN apk update && apk add --no-cache \
    postgresql-libs \
    postgresql-dev \
    git \
    curl \
    build-base \
    libffi-dev \
    openssl-dev \
    musl-dev

# Install Rust toolchain
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

STOPSIGNAL SIGINT

CMD ["python3", "main.py"]