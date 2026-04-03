# syntax=docker/dockerfile:1.21@sha256:27f9262d43452075f3c410287a2c43f5ef1bf7ec2bb06e8c9eeb1b8d453087bc
# =============================================================================
# Distroless Production Python Container
# =============================================================================
# This Dockerfile creates a minimal, secure container using Google's distroless
# base image for maximum security in production.
#
# Security features:
# - Multi-stage build to minimize attack surface
# - Non-root user execution (UID 65532)
# - No shell or package manager in runtime image
# - Minimal runtime dependencies
# - Distroless base image (no unnecessary OS components)
# - Multi-architecture support (amd64/arm64)
#
# Optimization features:
# - uv for all package installations
# - Bytecode compilation for faster startup
# - Railway-compatible (no cache mounts required)
#
# Build: docker build -f Dockerfile.distroless -t app:distroless .
# Multi-arch: docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.distroless -t app:distroless .
# =============================================================================

# -----------------------------------------------------------------------------
# Build Arguments
# -----------------------------------------------------------------------------
ARG PYTHON_VERSION=3.13
ARG DEBIAN_VERSION=bookworm
ARG BUILDER_IMAGE=docker.io/python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}
ARG RUN_IMAGE=gcr.io/distroless/cc-debian12:nonroot@sha256:7e5b8df2f4d36f5599ef4ab856d7d444922531709becb03f3368c6d797d0a5eb

# =============================================================================
# Stage 1: Python Base
# =============================================================================
# Minimal base image with build tools
# =============================================================================
FROM ${BUILDER_IMAGE} AS python-base

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        tini \
        unzip \
        ca-certificates \
    && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/* /var/log/* /tmp/*

# Install uv (fast Python package installer)
# Pin to specific version for reproducible builds
# For SHA256 pinning: COPY --from=ghcr.io/astral-sh/uv@sha256:<digest> /uv /uvx /bin/
COPY --from=ghcr.io/astral-sh/uv:latest@sha256:94a23af2d50e97b87b522d3cea24aaf8a1faedec1344c952767434f69585cbf9 /uv /uvx /bin/

# =============================================================================
# Stage 2: Builder
# =============================================================================
# Installs all dependencies and builds the application
# =============================================================================
FROM python-base AS builder

ARG UV_INSTALL_ARGS="--no-dev"

# Environment configuration for optimal builds
ENV GRPC_PYTHON_BUILD_WITH_CYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PATH="/workspace/app/.venv/bin:/usr/local/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    # Build-time settings to prevent connection attempts
    DATABASE_POOL_DISABLED=true \
    SAQ_USE_SERVER_LIFESPAN=false \
    SAQ_WEB_ENABLED=false

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/* /var/log/* /tmp/*

WORKDIR /workspace/app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock README.md ./

# Create virtual environment and install Python dependencies
RUN uv venv \
    && uv sync ${UV_INSTALL_ARGS} --frozen --no-install-project --no-editable \
    && uv export ${UV_INSTALL_ARGS} --frozen --no-hashes --no-emit-project --output-file=requirements.txt

# Copy application source
COPY app ./app

# Create wheel distribution for the application
RUN uv sync ${UV_INSTALL_ARGS} --frozen --no-editable \
    && uv build --wheel

# =============================================================================
# Stage 3: Runtime Preparation
# =============================================================================
# Prepares the runtime environment with Python and dependencies
# =============================================================================
FROM python-base AS runtime-prep

# Use TARGETARCH provided by Docker buildx for multi-arch support
ARG TARGETARCH

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Create non-root user matching distroless nonroot user
RUN groupadd --system --gid 65532 nonroot \
    && useradd --no-create-home --system --uid 65532 --gid 65532 nonroot \
    && mkdir -p /workspace/app \
    && chown -R nonroot:nonroot /workspace

# Create virtual environment with copied Python for distroless
RUN python -m venv --copies /workspace/app/.venv

# Copy requirements and wheel from builder
COPY --from=builder --chown=65532:65532 /workspace/app/requirements.txt /tmp/requirements.txt
COPY --from=builder --chown=65532:65532 /workspace/app/dist/*.whl /tmp/

WORKDIR /workspace/app

# Install dependencies into the virtual environment using uv
# uv is faster and more reliable than pip
RUN uv pip install \
        --quiet \
        --no-cache-dir \
        --no-deps \
        --requirement=/tmp/requirements.txt \
    && uv pip install \
        --quiet \
        --no-cache-dir \
        --no-deps \
        /tmp/*.whl \
    && rm -rf /tmp/*

# Detect architecture and create symlinks for library paths
# This enables the same Dockerfile to work on both amd64 and arm64
RUN ARCH_DIR=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64-linux-gnu" || echo "x86_64-linux-gnu") \
    && mkdir -p /runtime-libs/lib /runtime-libs/usr/lib \
    && cp -a /lib/${ARCH_DIR} /runtime-libs/lib/ \
    && cp -a /usr/lib/${ARCH_DIR} /runtime-libs/usr/lib/ \
    && echo "${ARCH_DIR}" > /runtime-libs/arch

# =============================================================================
# Stage 4: Distroless Runtime
# =============================================================================
# Minimal production image with no shell or package manager
# =============================================================================
FROM ${RUN_IMAGE} AS runtime

ENV PATH="/workspace/app/.venv/bin:/usr/local/bin:$PATH" \
    LITESTAR_APP="app.server.asgi:create_app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Copy Python interpreter and standard library
COPY --from=runtime-prep /usr/local/lib/ /usr/local/lib/
COPY --from=runtime-prep /usr/local/bin/python /usr/local/bin/python
COPY --from=runtime-prep /etc/ld.so.cache /etc/ld.so.cache

# Copy tini for proper signal handling
COPY --from=runtime-prep /usr/bin/tini /usr/local/bin/tini

# Copy required shared libraries (architecture-aware)
COPY --from=runtime-prep /runtime-libs/lib/ /lib/
COPY --from=runtime-prep /runtime-libs/usr/lib/ /usr/lib/
COPY --from=runtime-prep /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy the application virtual environment
WORKDIR /workspace/app
COPY --from=runtime-prep --chown=65532:65532 /workspace/app/.venv /workspace/app/.venv

# Container configuration
# Port is configured via LITESTAR_PORT env var (defaults to 8000)
STOPSIGNAL SIGTERM
EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/tini", "--"]
CMD ["app", "run", "--host", "0.0.0.0"]

# Labels for container metadata (OCI spec)
LABEL org.opencontainers.image.title="Sessions API" \
      org.opencontainers.image.description="Tūhura Tech Sessions management system" \
      org.opencontainers.image.vendor="Tūhura Tech" \
      org.opencontainers.image.licenses="AGPLv3-or-later" \
      org.opencontainers.image.base.name="gcr.io/distroless/cc-debian12:nonroot"