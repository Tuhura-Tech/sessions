# Frontend admin portal build
FROM docker.io/library/node:24-alpine@sha256:cd6fb7efa6490f039f3471a189214d5f548c11df1ff9e5b181aa49e22c14383e AS builder

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
FROM docker.io/library/nginx:alpine@sha256:b0f7830b6bfaa1258f45d94c240ab668ced1b3651c8a222aefe6683447c7bf55

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
