# Ejecuta benchmark secuencial para mezcla de modelos Ollama y privados
Push-Location (Split-Path $MyInvocation.MyCommand.Path -Parent)
cd ..

python run_tests.py --config config/config.benchmark.mixed.json

Pop-Location
