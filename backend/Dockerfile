FROM python:3.12-slim

# System deps: git, pandoc (export), nodejs (mermaid-cli), chromium (mmdc render),
# weasyprint runtime libs (PDF engine).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        pandoc \
        nodejs \
        npm \
        chromium \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libcairo2 \
        fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Mermaid CLI. Skip Puppeteer's bundled Chromium; use the system one.
ENV PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
RUN npm install -g @mermaid-js/mermaid-cli@11.4.2

# WeasyPrint (PDF engine for Pandoc).
RUN pip install --no-cache-dir weasyprint

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Puppeteer config so mmdc runs headless Chromium without a sandbox in-container.
COPY puppeteer.json /etc/puppeteer.json
ENV PUPPETEER_CONFIG=/etc/puppeteer.json

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
