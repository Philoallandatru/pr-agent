FROM python:3.12.10-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PR_AGENT_CONFIG_FILE=/app/.pr_agent.toml

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y git curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
COPY pr_agent ./pr_agent
COPY docs ./docs

RUN pip install --no-cache-dir .

RUN mkdir -p /data/state /data/repos /data/tokenizers

CMD ["python", "-m", "pr_agent.servers.bitbucket_server_polling"]
