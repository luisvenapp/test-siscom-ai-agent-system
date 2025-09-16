# Ejecuta el smoke test CLI en Docker
param(
  [string]$ComposeFile = "docker-compose.cli.yml"
)

Push-Location (Split-Path $MyInvocation.MyCommand.Path -Parent)
cd ..

docker build -t local/llm-tests:latest .
docker compose -f $ComposeFile up --build

Pop-Location
