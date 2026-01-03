FROM python:3.12-slim
LABEL project.home="https://github.com/Carton/MikaLendingBot"

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /usr/src/app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md default.cfg.example ./
RUN uv sync --frozen --no-cache --no-dev --no-install-project

# Copy source code (excluding configs per .dockerignore)
COPY src ./src
COPY www ./www

# Install the project
RUN uv sync --frozen --no-cache --no-dev

# Create directory for persistent data (configs, logs, etc.)
RUN mkdir -p /data/conf /data/market_data /data/log logs

# Default environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1

# Expose web server port
EXPOSE 8000


# Default command: run the bot with the provided config
# UV_NO_DEV environment variable ensures dev dependencies are not installed
CMD ["uv", "run", "lendingbot"]