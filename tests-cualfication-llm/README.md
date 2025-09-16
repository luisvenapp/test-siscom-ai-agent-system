# Sistema de Testing Avanzado para LLMs Locales

Este paquete crea un entorno aislado para evaluar de forma profesional múltiples modelos/agents LLM locales bajo escenarios controlados, con medición cuantitativa, cualitativa y calificativa.

Objetivos clave:
- Orquestación de pruebas de principio a fin por agente, escenario e iteración (≥ 10 por agente). Soporta ejecución secuencial por agente para benchmarking de múltiples modelos de Ollama.
- Métricas cuantitativas: latencia (p50/p95), throughput, longitud de respuesta, variabilidad entre iteraciones, errores.
- Métricas cualitativas: cobertura de keywords requeridas/prohibidas, formato, cumplimiento de instrucciones, coherencia básica.
- Métricas calificativas: scoring ponderado por rúbricas (exactitud, completitud, relevancia, claridad, estilo, penalización por tiempo excedido).
- Logging por test con convención: <agentName>__<timestamp>__iter-<N>.log
- Reportes agregados por agente y por escenario en JSON/CSV/Markdown.
- Adaptadores de agente: Ollama (HTTP), OpenAI, DeepSeek, Google Gemini (AI Studio, no Vertex), HTTP genérico (simple/OpenAI), CLI local. Extensible.

Estructura
- config/ → configuración principal y ejemplos
- scenarios/ → escenarios de prueba (JSON) con entradas y verdades-objetivo
- src/core → orquestación, ejecución, logging, carga de escenarios
- src/agents → interfaces y adaptadores de agentes
- src/metrics → cálculo de métricas y rúbricas
- src/reporting → agregación y exportación de reportes
- logs/ → archivos de log por test
- reports/ → reportes agregados

Diagrama general (Mermaid)
```mermaid
flowchart LR
    A[config/config.json] --> B[Orchestrator]
    S[scenarios/*.json] --> C[Scenario Loader]
    C --> B
    subgraph Agents
      D1[Ollama Adapter]
      D2[HTTP Adapter]
      D3[CLI Adapter]
    end
    B -->|prompts| D1
    B -->|prompts| D2
    B -->|prompts| D3
    D1 -->|respuestas| E[Metrics]
    D2 -->|respuestas| E
    D3 -->|respuestas| E
    E --> F[Aggregator]
    F --> G[Reporting JSON/CSV/MD]
    B --> H[Logs por prueba]
```

Quick start (Python 3.10+)
1) Ajusta config/config.json (agentes, iteraciones, timeouts, etc.)
   - Puedes mezclar agentes Ollama, OpenAI, DeepSeek y Gemini.
   - Usa agent_execution: "sequential" para benchmarking modelo por modelo.
2) Añade/modifica escenarios en scenarios/*.json
3) Ejecuta: `python run_tests.py`
- Benchmarks rápidos (PowerShell):
  - Ollama: `./scripts/run_benchmark_ollama.ps1`
  - Privados (OpenAI/DeepSeek/Gemini): `./scripts/run_benchmark_private.ps1`
  - Mixto: `./scripts/run_benchmark_mixed.ps1`
- Ver resultados:
  - `reports/summary__<timestamp>.md`
  - `reports/summary__<timestamp>.json`
  - `reports/summary__<timestamp>.csv`
  - `reports/dashboard__<timestamp>.html` (gráficos Plotly por agente)


Requisitos
- Solo usa librerías estándar por defecto (urllib, json, time, concurrent.futures). Opcionalmente puedes instalar librerías para métricas avanzadas, pero el sistema funciona sin dependencias externas.

Notas de diseño
- Transparencia: Cada prueba genera un log independiente con parámetros, tiempos, respuesta y métricas por iteración.
- Reproducibilidad: Se permite fijar parámetros del agente (por ejemplo temperatura) si el backend lo soporta.
- Extensibilidad: Añade nuevos adaptadores implementando BaseAgent en src/agents/base.py.
- Robustez: Manejo de timeouts y captura de errores por iteración para no detener campañas completas.

