# Ejecuta pruebas con backends reales usando docker-compose.yml
Push-Location (Split-Path $MyInvocation.MyCommand.Path -Parent)
cd ..

docker compose up --build

Pop-Location
