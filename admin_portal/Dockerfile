# Frontend admin portal build
FROM docker.io/library/node:24-alpine@sha256:2bdb65ed1dab192432bc31c95f94155ca5ad7fc1392fb7eb7526ab682fa5bf14 AS builder

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
FROM docker.io/library/nginx:alpine@sha256:645eda1c2477aaa9b879f73909b9222c6f19798dd45be6706268d82a661c6e6d

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
