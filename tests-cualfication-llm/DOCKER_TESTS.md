# Validación en Docker – pruebas smoke con agente CLI y pruebas contra backend

Objetivo: validar el sistema en entorno aislado sin depender de servidores externos (CLI) y, opcionalmente, ejecutar pruebas contra el backend FastAPI usando el endpoint auxiliar `/v1/test-completion`.

Pasos
1) Construir la imagen:
   ```bash
   cd tests-cualfication-llm
   docker build -t local/llm-tests:latest .
   ```

2A) Ejecutar docker-compose (escenario CLI):
   ```bash
   docker compose -f docker-compose.cli.yml up --build
   ```
   - Esto monta `scenarios_cli/` dentro del contenedor como `/app/scenarios`, usa `config/config.cli.json` y ejecuta las 10 iteraciones por caso.

2B) Ejecutar docker-compose (contra backend FastAPI):
   - Asegúrate de levantar el backend (puerto 8001)
   - Inicia las pruebas:
     ```bash
     docker compose -f docker-compose.backend.yml up --build
     ```
   - Esta configuración usa `config/config.backend.json` apuntando a `http://host.docker.internal:8001/v1/test-completion`.

3) Ver artefactos:
   - `logs/` en el host: archivos por iteración con nombres `<agent>__<timestamp>__iter-<N>__<escenario>__<case>.log`.
   - `reports/` en el host:
     - `raw_results__<timestamp>.json`
     - `summary__<timestamp>.{json,md,csv}`

4) Resultado esperado (CLI eco):
   - Caso `echo_short` con prompt `OK` → exact_match_any debe cumplir, latencia baja, score alto.
   - Caso `echo_list` con 3 líneas de lista → format.list y min_items cumplidos, score alto.

5) Finalizar:
   ```bash
   docker compose -f docker-compose.cli.yml down
   docker compose -f docker-compose.backend.yml down
   ```

Notas
- El smoke-test CLI no requiere Ollama ni endpoints HTTP. Aísla la validación del framework.
- Para conectar con Ollama/HTTP en el host, usa `docker-compose.yml` y ajusta `config/config.json` con `host.docker.internal`.
