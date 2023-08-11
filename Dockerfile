# syntax=docker/dockerfile:1

FROM python:3.9-bullseye

WORKDIR /bancho

# Install python dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy source code
COPY . .

CMD ["python3", "main.py"]