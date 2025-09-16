# Ejecuta benchmark secuencial para modelos Ollama
Push-Location (Split-Path $MyInvocation.MyCommand.Path -Parent)
cd ..

python run_tests.py --config config/config.benchmark.ollama.json

Pop-Location
