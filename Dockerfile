FROM python:3.12-slim
LABEL project.home="https://github.com/Carton/MikaLendingBot"

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /usr/src/app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

# Copy the rest of the source code
COPY . .

# Create directory for persistent data (configs, logs, etc.)
RUN mkdir -p /data/conf /data/market_data /data/log

# Default environment variables
ENV PYTHONUNBUFFERED=1

# Expose web server port
EXPOSE 8000

# Default command: run the bot with the provided config
# If no config is provided, it will fallback to looking for default.cfg in the working dir
CMD ["uv", "run", "python", "-m", "lendingbot.main"]
