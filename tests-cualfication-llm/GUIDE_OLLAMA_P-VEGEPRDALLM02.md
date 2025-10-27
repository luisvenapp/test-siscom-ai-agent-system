# Guía de pruebas para modelos Ollama en P-VEGEPRDALLM02

Esta guía explica cómo ejecutar los tests de calificación/benchmark contra los modelos desplegados en:

- Servidor: P-VEGEPRDALLM02.nlt.local
- Puerto: 11434
- Endpoint: http://P-VEGEPRDALLM02.nlt.local:11434

La configuración y el runner ya están incluidos en este repo.

## 1) Requisitos previos

- VPN conectada a la red corporativa (ya indicado en el requerimiento)
- Python 3.10+
- Dependencias del framework de pruebas (desde la raíz del repo):
  - Si no has configurado aún el entorno del proyecto, instala dependencias del submódulo de pruebas si aplica.

> Nota: El runner no requiere librerías externas para llamar a Ollama; utiliza urllib de la stdlib.

## 2) Configuración incluida

Se agregó el archivo de configuración listo para usar:

- tests-cualfication-llm/config/config.benchmark.ollama.vegeprd.json

Este archivo declara TODOS los modelos solicitados, apuntando al servidor remoto y utiliza escenarios genéricos ya presentes en `tests-cualfication-llm/scenarios/`.

Parámetros principales:
- iterations: 2 (para una pasada rápida). Aumenta si quieres más estabilidad estadística.
- timeout_seconds: 240 (modelos grandes pueden tardar más).
- max_model_fail_retries: 1 (un reintento por fallo puntual).
- agent_execution: "sequential" y within_agent_concurrency: 1 (recomendado para no saturar el servidor). Puedes subirlo bajo tu propio criterio.

## 3) Lista de modelos configurados

Ultra Grandes (60GB+):
- aravhawk/llama4:109b
- gpt-oss:120b
- mixtral:8x22b

Grandes (20–50GB):
- deepseek-r1:70b
- llama3.3:70b
- phi4:14b-fp16
- mixtral:8x7b

Medianos (10–20GB):
- deepseek-r1:32b
- qwen3:32b
- gemma3:27b
- devstral:24b
- devstral:latest
- gpt-oss:20b

Rápidos (2–10GB):
- deepseek-r1:14b
- qwen2.5:14b
- gemma3:12b
- gemma2:9b
- deepseek-r1:8b
- llama3:8b
- qwen2.5:7b
- phi3.5:3.8b

Todos con base_url = http://P-VEGEPRDALLM02.nlt.local:11434 y parámetros por defecto:
- temperature: 0.2
- top_p: 0.9
- num_predict: 512

Puedes ajustar estos parámetros por modelo en el propio JSON.

## 4) Cómo ejecutar las pruebas

Desde la raíz del repositorio:

1. Ir a la carpeta del framework de pruebas:
   cd tests-cualfication-llm

2. Ejecutar el runner con la nueva config:
   python -m run_tests --config config/config.benchmark.ollama.vegeprd.json

Durante la ejecución verás el progreso en consola. Al finalizar se generan reportes en `tests-cualfication-llm/reports/` con timestamp.

Archivos de salida típicos:
- reports/summary__YYYYMMDD-HHMMSS.json
- reports/summary__YYYYMMDD-HHMMSS.md
- reports/summary__YYYYMMDD-HHMMSS.csv
- reports/dashboard__YYYYMMDD-HHMMSS.html (dashboard interactivo)
- reports/raw_results__YYYYMMDD-HHMMSS.json (resultados crudos)

Logs detallados por agente/escenario/caso en:
- tests-cualfication-llm/logs/

## 5) Cómo modificar qué modelos o escenarios se ejecutan

- Edita `tests-cualfication-llm/config/config.benchmark.ollama.vegeprd.json`:
  - Para deshabilitar un modelo, elimina su entrada en `agents` o coméntala (si prefieres, copia el archivo y ten variantes).
  - Para cambiar parámetros (temperature, top_p, num_predict), edítalos por agente.
  - Para cambiar timeouts, ajusta `timeout_seconds`.
  - Para ejecutar en paralelo dentro de cada agente (multiprocesar casos), sube `within_agent_concurrency` (p.ej., 2 o 4). Usa con cuidado para no impactar el host.
  - Para ejecutar varios agentes al mismo tiempo, cambia `agent_execution` a "parallel" y ajusta `concurrency`.

- Escenarios:
  - Los JSON están en `tests-cualfication-llm/scenarios/`. Puedes duplicar y crear tus propios casos. Asegúrate de que cada escenario tenga:
    {
      "name": "<nombre>",
      "cases": [
        {"id": "case-1", "prompt": "<texto>", "expected": {"must_include": ["..."], "must_not_include": ["..."], "format": {}}}
      ]
    }
  - La carpeta de escenarios utilizada por la config se define en `scenarios_dir`.

## 6) Recomendaciones prácticas

- Los modelos muy grandes pueden tener latencias elevadas. Mantén `iterations` bajo para validación rápida; súbelo (p.ej., 5–10) para benchmark.
- Si el servidor reporta errores intermitentes, `max_model_fail_retries` puede ayudar.
- `num_predict` controla el máximo de tokens de salida. Reducirlo acelera las pruebas y evita respuestas demasiado largas.
- Si sólo quieres hacer un "smoke test", puedes apuntar `scenarios_dir` a `scenarios_smoke` y bajar `iterations` a 1.

## 7) Costeo y ranking (opcional)

El agregador permite estimar costos si agregas en la config:

"cost_per_1k_output_tokens": {
  "ollama_llama4_109b": 0.000,  
  "ollama_mixtral_8x22b": 0.000
}

Los valores son libres (USD por 1K tokens de salida). Se incorporan al dashboard y al ranking compuesto. También puedes habilitar `include_error_breakdown: true` para ver top de errores agrupados.

## 8) Solución de problemas

- Error de conexión: verifica VPN y resolución DNS hacia P-VEGEPRDALLM02.nlt.local. Prueba: `curl http://P-VEGEPRDALLM02.nlt.local:11434/api/tags`.
- Timeout: incrementa `timeout_seconds` o reduce `num_predict`.
- Memoria o saturación en host: ejecuta con `agent_execution: sequential` y `within_agent_concurrency: 1`.
- Modelo no encontrado: valida que el tag exista en el servidor con `/api/tags` o con `ollama list` si tienes acceso. Ajusta `model` en la config.

## 9) Ejecución rápida por grupo de tamaño

Puedes crear variantes del archivo para grupos, por ejemplo sólo "Rápidos": duplica el JSON y deja únicamente los agentes rápidos. Luego:

python -m run_tests --config config/config.benchmark.ollama.vegeprd.rapidos.json

## 10) Estructura interna del runner (por si necesitas ajustar)

- Runner: tests-cualfication-llm/run_tests.py
- Orquestador: src/core/orchestrator.py
- Agente Ollama: src/agents/ollama_agent.py (usa /api/generate y maneja ND-JSON)
- Métricas y scoring: src/metrics/
- Reportes y dashboard: src/reporting/

Cualquier duda o si quieres que genere variantes pre-hechas (por tamaño, por temperatura, etc.), avísame y las agrego.
