FROM python:3.11-slim

# Non-root user for safety checks
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Install deps first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY quantities.py tool.json mcp_server.py ./

# Own the files as app user
RUN chown -R app:app /app
USER app

# MCP stdio server — talks via stdin/stdout, no ports
CMD ["python", "mcp_server.py"]
