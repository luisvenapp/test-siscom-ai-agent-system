# Ejecuta benchmark secuencial para modelos privados (OpenAI, DeepSeek, Gemini)
Push-Location (Split-Path $MyInvocation.MyCommand.Path -Parent)
cd ..

python run_tests.py --config config/config.benchmark.private.json

Pop-Location
