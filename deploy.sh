#!/bin/bash

set -e  # Exit on error

echo "📦 Pulling latest code from Git..."
git pull origin main

# Define the production compose file and project name for isolation
PROD_COMPOSE_FILE="docker-compose.yml"
PROD_PROJECT_NAME="siscom-prod"

echo "🚀 Deploying updated containers..."
docker compose -f $PROD_COMPOSE_FILE -p $PROD_PROJECT_NAME up -d --build

echo "📋 Checking container status..."
docker compose -f $PROD_COMPOSE_FILE -p $PROD_PROJECT_NAME ps

echo "✅ Deployment completed successfully!"