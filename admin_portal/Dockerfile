# Frontend admin portal build
FROM docker.io/library/node:24-alpine@sha256:01743339035a5c3c11a373cd7c83aeab6ed1457b55da6a69e014a95ac4e4700b AS builder

# Build-time argument for API base URL (must be set at build time)
# Usage: docker build --build-arg PUBLIC_BASE_URL=https://api.example.com
ARG PUBLIC_BASE_URL=http://localhost:8000

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY . .

# Build the app with PUBLIC_BASE_URL embedded in static files
RUN VITE_PUBLIC_BASE_URL=${PUBLIC_BASE_URL} pnpm run build

# Production image
FROM docker.io/library/nginx:alpine@sha256:1d13701a5f9f3fb01aaa88cef2344d65b6b5bf6b7d9fa4cf0dca557a8d7702ba

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
