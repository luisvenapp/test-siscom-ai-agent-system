# Ejecuta pruebas contra el backend FastAPI usando docker-compose.backend.yml
Push-Location (Split-Path $MyInvocation.MyCommand.Path -Parent)
cd ..

docker build -t local/llm-tests:latest .
docker compose -f docker-compose.backend.yml up --build

Pop-Location
