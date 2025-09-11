# Multi-stage Dockerfile for Agentic Neurodata Conversion
# Uses pixi for consistent dependency management

# Stage 1: Base image with pixi
FROM mambaorg/micromamba:1.5.8 as base

# Set environment variables
ENV PIXI_VERSION=v0.13.0
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install pixi
USER root
RUN curl -fsSL https://pixi.sh/install.sh | bash
ENV PATH="/root/.pixi/bin:$PATH"

# Create app directory and set ownership
WORKDIR /app
RUN chown -R $MAMBA_USER:$MAMBA_USER /app

# Switch to non-root user
USER $MAMBA_USER

# Stage 2: Development image
FROM base as development

# Copy pixi configuration files
COPY --chown=$MAMBA_USER:$MAMBA_USER pixi.toml pyproject.toml ./

# Install dependencies using pixi
RUN pixi install --environment dev

# Copy source code
COPY --chown=$MAMBA_USER:$MAMBA_USER . .

# Install the package in editable mode
RUN pixi run pip install -e .

# Expose ports
EXPOSE 8000 8001

# Default command for development
CMD ["pixi", "run", "server-dev"]

# Stage 3: Production image
FROM base as production

# Copy pixi configuration files
COPY --chown=$MAMBA_USER:$MAMBA_USER pixi.toml pyproject.toml ./

# Install only production dependencies
RUN pixi install --environment prod

# Copy source code (excluding development files)
COPY --chown=$MAMBA_USER:$MAMBA_USER agentic_neurodata_conversion/ ./agentic_neurodata_conversion/
COPY --chown=$MAMBA_USER:$MAMBA_USER config/ ./config/
COPY --chown=$MAMBA_USER:$MAMBA_USER scripts/run_*.py ./scripts/
COPY --chown=$MAMBA_USER:$MAMBA_USER README.md LICENSE ./

# Install the package
RUN pixi run pip install .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs /app/temp

# Set environment variables for production
ENV AGENTIC_CONVERTER_ENV=production
ENV AGENTIC_CONVERTER_CONFIG_FILE=/app/config/docker.json
ENV AGENTIC_CONVERTER_DATA_DIR=/app/data
ENV AGENTIC_CONVERTER_TEMP_DIR=/app/temp
ENV AGENTIC_CONVERTER_LOG_LEVEL=INFO

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pixi run python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Default command for production
CMD ["pixi", "run", "server-prod"]

# Stage 4: Testing image
FROM development as testing

# Install test dependencies
RUN pixi install --environment test

# Copy test files
COPY --chown=$MAMBA_USER:$MAMBA_USER tests/ ./tests/

# Run tests by default
CMD ["pixi", "run", "test-ci"]
