# Python slim image; adjust version if needed.
FROM python:3.13-slim


WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY app ./app


CMD ["python", "-m", "app.main"]
