#!/bin/sh
set -e

echo "Starting Kafka consumer..."
python backend/workers/agent_consumer.py &
KAFKA_PID=$!

echo "Starting Uvicorn server with ${UVICORN_WORKERS:-2} workers..."
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --workers "${UVICORN_WORKERS:-2}" &
UVICORN_PID=$!

# Esperar a que uno muera
while true; do
  if ! kill -0 $KAFKA_PID 2>/dev/null; then
    echo "Kafka consumer died. Exiting..."
    exit 1
  fi
  if ! kill -0 $UVICORN_PID 2>/dev/null; then
    echo "Uvicorn died. Exiting..."
    exit 1
  fi
  sleep 5
done
