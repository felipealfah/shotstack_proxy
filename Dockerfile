# Root Dockerfile for development convenience
# This builds the entire stack in development mode

FROM node:18-alpine AS base
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache python3 py3-pip curl

# Copy package files
COPY apps/web/package*.json ./apps/web/
COPY apps/intermediary/requirements.txt ./apps/intermediary/

# Install Node.js dependencies
WORKDIR /app/apps/web
RUN npm ci

# Install Python dependencies
WORKDIR /app/apps/intermediary
RUN pip install -r requirements.txt

# Copy source code
WORKDIR /app
COPY . .

# Expose ports
EXPOSE 3000 8000

# Default command (can be overridden in docker-compose)
CMD ["echo", "Use docker-compose to run individual services"]