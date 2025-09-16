# Plan de ejecución por fases

Objetivo: ejecutar y validar el sistema paso a paso, desde un smoke test aislado hasta pruebas completas con backends reales, ajustando rúbricas y escenarios con base en los resultados.

Fase 1 — Preflight
- Requisitos: Docker Desktop o Docker Engine. (Opcional: Python 3.10+ para pruebas locales)
- Revisa `GUIDE.md` y `DOCKER_TESTS.md`.

Fase 2 — Smoke test en Docker con agente CLI (aislado)
1) Construye la imagen:
   - `docker build -t local/llm-tests:latest .`
2) Ejecuta el smoke test:
   - `docker compose -f docker-compose.cli.yml up --build`
3) Verifica artefactos:
   - `logs/`: nombres `<agent>__<timestamp>__iter-<N>__cli_echo__<case>.log`
   - `reports/summary__<timestamp>.{json,md,csv}` y `raw_results__<timestamp>.json`
4) Esperado: ok_rate ≈ 100%, latencias bajas, grades altos.
5) Finaliza:
   - `docker compose -f docker-compose.cli.yml down`

Fase 3 — Pruebas con backends reales (Ollama/HTTP)
1) Ajusta `config/config.json`:
   - Para servicios del host desde contenedor (Win/Mac): `http://host.docker.internal:<puerto>`.
   - O usa variables de entorno en config con `${VAR}` (expansión activada).
2) Ejecuta:
   - `docker compose up --build`
3) Verifica artefactos en `logs/` y `reports/`.

Fase 4 — Análisis y calibración de rúbricas
1) Abre `reports/summary__<timestamp>.md`:
   - Revisa `ok_rate`, latencia `p50/p95/avg/std`, `throughput_rps`, `score avg/std`, `grades`.
2) Ajusta pesos/umbrales en `config/config.json` → `rubrics.weights`/`rubrics.thresholds`.
3) Ajusta escenarios (`scenarios/*.json`) para cubrir casos reales: must_include/must_not_include, formato JSON/listas, exact_match, etc.

Fase 5 — Escalado y cobertura
1) Concurrency: sube `concurrency` gradualmente.
2) Baselines y comparativas: duplica agentes con distintas configuraciones para comparar (temperatura, top_p, num_predict/modelos).
3) Añade escenarios por dominio: legal, finanzas, soporte, RAG, seguridad avanzada.

Fase 6 — Operación continua
1) Limpieza de artefactos (logs/reports) según política.
2) CI/CD (opcional): integra el build + compose up nocturno.
3) Seguridad: usa `${VAR}` en config y define envs en docker-compose para secretos.

Comandos rápidos
- Smoke test: `docker compose -f docker-compose.cli.yml up --build`
- Backends reales: `docker compose up --build`
- Down: `docker compose down` (o con `-f docker-compose.cli.yml`)
