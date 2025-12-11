FROM ghcr.io/prefix-dev/pixi:latest

WORKDIR /app

# Copy only what's needed for dependency resolution first (better layer caching)
COPY pixi.toml pixi.lock pyproject.toml README.md ./

# Application code (includes kg_service + ontologies)
COPY agentic_neurodata_conversion ./agentic_neurodata_conversion

# Install the locked environment
RUN pixi install --frozen

# Prefer running the installed environment directly (avoid invoking pixi at runtime).
ENV PATH="/app/.pixi/envs/default/bin:${PATH}"

EXPOSE 8001

CMD ["uvicorn", "agentic_neurodata_conversion.kg_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
