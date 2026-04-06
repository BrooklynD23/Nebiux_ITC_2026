FROM node:20-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ .

EXPOSE 5173

# --host exposes Vite's dev server to the Docker network (required inside container)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
