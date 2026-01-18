FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add waitress for Windows compatibility
RUN pip install --no-cache-dir waitress

COPY . .

RUN mkdir -p /app/reports

EXPOSE 5000

# Use waitress which works well on Windows
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "wsgi:app"]