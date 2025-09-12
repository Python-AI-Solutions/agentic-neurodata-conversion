# Deployment Guide

This guide covers deployment options for the Agentic Neurodata Conversion system
using Docker and Kubernetes.

## Prerequisites

### Docker Deployment

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose v2.0+
- 4GB+ RAM available
- 10GB+ disk space

### Kubernetes Deployment

- Kubernetes cluster 1.20+
- kubectl configured for cluster access
- Docker registry access (for image storage)
- 8GB+ RAM available across nodes
- 50GB+ persistent storage

## Available Pixi Tasks

The deployment system provides convenient pixi tasks for all operations. Run
`pixi run deploy-help` to see all available tasks:

### Docker Deployment Tasks

- `pixi run deploy-dev` - Start development environment
- `pixi run deploy-prod` - Start production environment
- `pixi run deploy-test` - Run tests in container
- `pixi run deploy-stop` - Stop all services
- `pixi run deploy-status` - Show deployment status
- `pixi run deploy-logs` - Show service logs
- `pixi run deploy-build` - Build Docker images
- `pixi run deploy-clean` - Clean up containers and volumes

### Kubernetes Deployment Tasks

- `pixi run k8s-deploy` - Deploy to Kubernetes
- `pixi run k8s-update` - Update Kubernetes deployment
- `pixi run k8s-status` - Show Kubernetes status
- `pixi run k8s-logs` - Show Kubernetes logs
- `pixi run k8s-delete` - Delete Kubernetes deployment

### Health Check Tasks

- `pixi run health-check` - Run health check
- `pixi run health-check-json` - Health check with JSON output
- `pixi run health-check-quiet` - Quiet health check (for scripts)

### Setup Tasks

- `pixi run setup-dev-env` - Setup development environment
- `pixi run setup-prod-env` - Setup production environment

### Docker Image Tasks

- `pixi run docker-build` - Build Docker images
- `pixi run docker-pull` - Pull latest images
- `pixi run docker-push` - Push images to registry (requires REGISTRY env var)

## Quick Start

### Development Environment

1. **Clone and setup**:

   ```bash
   git clone <repository-url>
   cd agentic-neurodata-conversion
   pixi run setup-dev-env
   ```

2. **Start development environment**:

   ```bash
   pixi run deploy-dev
   ```

3. **Access services**:
   - MCP Server: http://localhost:8000
   - HTTP API: http://localhost:8080 (if enabled)
   - API Documentation: http://localhost:8080/docs

### Production Environment

1. **Configure environment**:

   ```bash
   pixi run setup-prod-env
   # Edit .env with production settings
   ```

2. **Deploy production**:
   ```bash
   pixi run deploy-prod
   ```

## Docker Deployment

### Environment Configuration

The system uses environment variables for configuration. Copy `.env.docker` to
`.env` and customize:

```bash
# Application Environment
AGENTIC_CONVERTER_ENV=production
CONFIG_FILE=docker.json
LOG_LEVEL=INFO

# Server Ports
MCP_SERVER_PORT=8000
HTTP_SERVER_PORT=8080

# Database (optional)
POSTGRES_DB=agentic_converter
POSTGRES_USER=agentic
POSTGRES_PASSWORD=secure_password

# Security
API_KEY=your-secure-api-key
ALLOWED_ORIGINS=https://yourdomain.com
```

### Service Profiles

The Docker Compose setup supports multiple profiles:

- **Default**: MCP server only
- **http**: Adds HTTP API server
- **cache**: Adds Redis for caching
- **database**: Adds PostgreSQL for persistence
- **test**: Testing environment
- **docs**: Documentation server

### Deployment Commands

```bash
# Development with all services
pixi run deploy-dev

# Production deployment
pixi run deploy-prod

# Testing
pixi run deploy-test

# View status
pixi run deploy-status

# View logs
pixi run deploy-logs

# Stop services
pixi run deploy-stop

# Clean up everything
pixi run deploy-clean
```

### Manual Docker Compose

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With specific profiles
docker-compose --profile cache --profile database up -d

# Scale services
docker-compose up -d --scale mcp-server=3
```

## Kubernetes Deployment

### Cluster Requirements

- **CPU**: 2+ cores recommended
- **Memory**: 8GB+ recommended
- **Storage**: 100GB+ persistent volume
- **Networking**: Ingress controller (nginx recommended)
- **TLS**: cert-manager for automatic certificates (optional)

### Configuration

1. **Update Kubernetes config**:

   ```bash
   # Edit k8s/configmap.yaml
   # Update domain in k8s/ingress.yaml
   ```

2. **Configure storage class**:
   ```bash
   # Edit k8s/pvc.yaml
   # Set appropriate storageClassName for your cluster
   ```

### Deployment Commands

```bash
# Full deployment
pixi run k8s-deploy

# With custom image tag and registry
IMAGE_TAG=v1.0.0 REGISTRY=your-registry.com pixi run k8s-deploy

# Update deployment
pixi run k8s-update

# Check status
pixi run k8s-status

# View logs
pixi run k8s-logs

# Delete deployment
pixi run k8s-delete
```

### Manual Kubernetes Deployment

```bash
# Apply all resources
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n agentic-neurodata

# Port forward for testing
kubectl port-forward service/agentic-mcp-service 8000:8000 -n agentic-neurodata

# View logs
kubectl logs -l app.kubernetes.io/component=mcp-server -n agentic-neurodata -f
```

## Configuration Management

### Environment-Specific Configs

The system supports multiple configuration files:

- `config/default.json` - Default settings
- `config/docker.json` - Docker container settings
- `config/kubernetes.json` - Kubernetes deployment settings
- `config/production.json` - Production overrides
- `config/testing.json` - Testing configuration

### Configuration Hierarchy

1. Environment variables (highest priority)
2. Configuration file specified by `AGENTIC_CONVERTER_CONFIG_FILE`
3. Default configuration file
4. Built-in defaults (lowest priority)

### Key Configuration Options

```json
{
  "http": {
    "host": "0.0.0.0",
    "port": 8000,
    "enable_openapi": true
  },
  "agents": {
    "timeout_seconds": 600,
    "max_concurrent_tasks": 8,
    "memory_limit_mb": 2048
  },
  "security": {
    "enable_authentication": true,
    "rate_limit_requests_per_minute": 1000
  },
  "logging": {
    "level": "INFO",
    "enable_structured_logging": true
  }
}
```

## Health Checks and Monitoring

### Health Check Endpoints

- `GET /health` - Basic health check
- `GET /status` - Detailed system status
- `GET /metrics` - Prometheus metrics (if enabled)

### Docker Health Checks

Built-in health checks are configured in the Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pixi run python scripts/health_check.py --quiet
```

### Kubernetes Health Checks

Liveness and readiness probes are configured:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
```

### Manual Health Check

```bash
# Docker
pixi run health-check

# JSON output
pixi run health-check-json

# Quiet mode (for scripts)
pixi run health-check-quiet

# Kubernetes
kubectl exec -it deployment/agentic-mcp-server -n agentic-neurodata -- \
  pixi run health-check
```

## Scaling and Performance

### Docker Scaling

```bash
# Scale MCP server
docker-compose up -d --scale mcp-server=3

# With load balancer (requires additional setup)
docker-compose --profile loadbalancer up -d --scale mcp-server=3
```

### Kubernetes Scaling

```bash
# Manual scaling
kubectl scale deployment agentic-mcp-server --replicas=5 -n agentic-neurodata

# Horizontal Pod Autoscaler
kubectl autoscale deployment agentic-mcp-server \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n agentic-neurodata
```

### Performance Tuning

Key configuration parameters for performance:

```json
{
  "agents": {
    "max_concurrent_tasks": 8,
    "memory_limit_mb": 2048
  },
  "tools": {
    "max_concurrent_executions": 16
  },
  "performance": {
    "worker_pool_size": 4,
    "queue_max_size": 2000,
    "cache_size_mb": 512
  }
}
```

## Security Considerations

### Authentication

```json
{
  "security": {
    "enable_authentication": true,
    "api_key_header": "X-API-Key"
  }
}
```

Set API key via environment variable:

```bash
export AGENTIC_CONVERTER_API_KEY="your-secure-api-key"
```

### Network Security

- Use HTTPS in production (configure ingress with TLS)
- Restrict CORS origins
- Enable rate limiting
- Use network policies in Kubernetes

### Container Security

- Runs as non-root user (UID 1000)
- Read-only root filesystem where possible
- Minimal attack surface with distroless base images
- Security scanning in CI/CD pipeline

## Troubleshooting

### Common Issues

1. **Container won't start**:

   ```bash
   # Check logs
   pixi run deploy-logs

   # Check configuration
   pixi run health-check
   ```

2. **Service unreachable**:

   ```bash
   # Check deployment status
   pixi run deploy-status

   # Test connectivity
   pixi run health-check
   ```

3. **Performance issues**:

   ```bash
   # Check resource usage
   docker stats

   # Kubernetes resource usage
   kubectl top pods -n agentic-neurodata
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Docker
AGENTIC_CONVERTER_LOG_LEVEL=DEBUG docker-compose up

# Kubernetes
kubectl set env deployment/agentic-mcp-server \
  AGENTIC_CONVERTER_LOG_LEVEL=DEBUG \
  -n agentic-neurodata
```

### Log Collection

```bash
# Docker logs
docker-compose logs --tail=100 -f

# Kubernetes logs
kubectl logs -l app.kubernetes.io/component=mcp-server \
  -n agentic-neurodata \
  --tail=100 -f
```

## Backup and Recovery

### Data Backup

```bash
# Docker volumes
docker run --rm -v agentic-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/data-backup.tar.gz /data

# Kubernetes persistent volumes
kubectl exec -it deployment/agentic-mcp-server -n agentic-neurodata -- \
  tar czf /tmp/backup.tar.gz /app/data
kubectl cp agentic-neurodata/pod-name:/tmp/backup.tar.gz ./backup.tar.gz
```

### Configuration Backup

```bash
# Export Kubernetes configs
kubectl get configmap agentic-config -n agentic-neurodata -o yaml > config-backup.yaml
kubectl get configmap agentic-app-config -n agentic-neurodata -o yaml > app-config-backup.yaml
```

## Maintenance

### Updates

```bash
# Docker update
pixi run deploy-stop
pixi run docker-pull
pixi run deploy-prod

# Kubernetes rolling update
IMAGE_TAG=v1.1.0 pixi run k8s-update
```

### Cleanup

```bash
# Docker cleanup
pixi run deploy-clean

# Kubernetes cleanup
pixi run k8s-delete
```

This deployment guide provides comprehensive coverage of containerization and
deployment options for the Agentic Neurodata Conversion system.
