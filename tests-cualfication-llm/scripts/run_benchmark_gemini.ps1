# Ejecuta benchmark secuencial sólo para modelos Gemini (AI Studio)
Push-Location (Split-Path $MyInvocation.MyCommand.Path -Parent)
cd ..

python run_tests.py --config config/config.benchmark.gemini.json

Pop-Location
