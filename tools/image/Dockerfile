FROM python:3.12-slim-bookworm
ARG VERSION="latest"

EXPOSE 15400

# Metadata
LABEL org.opencontainers.image.source=https://github.com/sdsc-ordes/imaging-plaza-search
LABEL org.opencontainers.image.licenses=AGPL-3.0
LABEL org.opencontainers.image.title="Imaging-plaza-search API"
LABEL org.opencontainers.image.description="API for searching imaging plaza graph."
LABEL org.opencontainers.image.version=${VERSION}

# install uv
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /uvx /bin/

# install git
RUN apt-get update && apt-get install -y git && apt-get clean

WORKDIR /app
ADD CHANGELOG.md LICENSE README.md pyproject.toml uv.lock /app 
ADD src ./src
RUN uv sync --frozen
ENTRYPOINT ["uv", "run", "uvicorn", "src.imaging_plaza_search.main:app", "--reload", "--host", "0.0.0.0", "--port", "15400"]