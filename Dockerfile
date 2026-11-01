FROM node:22-slim AS proxy
RUN npm install -g mcp-proxy@6.7.16

FROM python:3.12-slim
ENV GLAMA_VERSION="1.1.0" \
    PYTHONUNBUFFERED=1
# mcp-proxy (Node) ships in a separate stage so the runtime image needs no
# apt/npm at build time. The previous Dockerfile re-cloned the repo at a
# hard-pinned SHA (db403ae, v1.0.0), so directory builds introspected the old
# tool schema (mul, convert) long after v1.1.0 shipped add/sub/div. Building
# from the build context keeps the image on the commit Glama indexes.
COPY --from=proxy /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=proxy /usr/local/bin/node /usr/local/bin/node
RUN ln -s /usr/local/lib/node_modules/mcp-proxy/dist/index.js /usr/local/bin/mcp-proxy \
    && node --version
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["mcp-proxy","--","python","mcp_server.py"]
