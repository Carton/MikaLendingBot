FROM python:3.12-slim
LABEL "project.home"="https://github.com/BitBotFactory/poloniexlendingbot"

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /usr/src/app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

COPY . .

# Set up volumes and links
VOLUME /data
RUN mkdir -p /data/market_data /data/log && \
    ln -sf /data/market_data market_data && \
    ln -sf /data/log/botlog.json www/botlog.json

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "lendingbot.main", "-cfg", "/data/conf/default.cfg"]
