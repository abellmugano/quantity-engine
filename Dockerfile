FROM debian:trixie-slim
ENV DEBIAN_FRONTEND=noninteractive \
    GLAMA_VERSION="1.0.0" \
    PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git && curl -fsSL https://deb.nodesource.com/setup_26.x | bash - && apt-get install -y --no-install-recommends nodejs && npm install -g mcp-proxy@6.7.16 pnpm@10.14.0 && node --version && curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR="/usr/local/bin" sh && uv python install 3.14 --default --preview && ln -s $(uv python find) /usr/local/bin/python && python --version && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
WORKDIR /app
RUN git clone https://github.com/abellmugano/quantity-engine . && git checkout db403aeff80894ae7b8fdc2cc27b6b92fe42e128
RUN python -m ensurepip --upgrade && python -m pip install --no-cache-dir -r requirements.txt
ENV PATH="/app/node_modules/.bin:$PATH"
CMD ["mcp-proxy","--","python","mcp_server.py"]