# Guía de Uso y Operación – Sistema de Testing Avanzado de LLMs Locales

Esta guía explica cómo instalar, configurar, ejecutar y extender el sistema de pruebas de LLMs locales contenido en `tests-cualfication-llm/`.

1) Objetivo
- Ejecutar campañas de testing contra múltiples agentes/modelos LLM locales.
- Medir desempeño cuantitativo (latencia, throughput, longitudes), cualitativo (cobertura de keywords, formato) y calificativo (score ponderado + calificación ≥/ < umbrales).
- Generar logs detallados por iteración y reportes agregados (JSON/Markdown/CSV) por agente y escenario.

2) Requisitos
- Python 3.10 o superior.
- Acceso a los backends locales definidos (Ollama/HTTP/CLI) y sus puertos/paths.
- Sistema operativo: Windows o Linux. La guía usa Windows como ejemplo.

3) Preparación del entorno (opcional, recomendado)
- Windows (PowerShell):
  ```powershell
  cd .\tests-cualfication-llm
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python --version
  ```
- Linux/MacOS (bash):
  ```bash
  cd tests-cualfication-llm
  python3 -m venv .venv
  source .venv/bin/activate
  python --version
  ```

4) Estructura del proyecto
- `config/config.json` – configuración global (iteraciones, timeouts, agentes, rúbricas, rutas).
- `scenarios/*.json` – definición de escenarios y casos de prueba.
- `src/core` – orquestación, registro y utilidades.
- `src/agents` – adaptadores de agentes (Ollama/HTTP/CLI) y base para extender.
- `src/metrics` – métricas y agregación ponderada.
- `src/reporting` – agregadores y exportadores (JSON/MD/CSV).
- `logs/` – logs por iteración (un archivo por ejecución de caso e iteración).
- `reports/` – resultados crudos y resúmenes agregados.
- `run_tests.py` – punto de entrada de pruebas.

5) Configuración (config/config.json)
Parámetros clave:
- `iterations`: mínimo 10 recomendado (se usa 10 por defecto).
- `concurrency`: número de hilos en paralelo (1 por defecto). Ajusta según capacidad del servidor.
- `timeout_seconds`: timeout por inferencia.
- `log_dir`, `reports_dir`, `scenarios_dir`: rutas relativas dentro de la carpeta de tests.
- `agents`: lista de agentes. Ejemplos:
  - Ollama:
    ```json
    {
      "name": "ollama_llama3_8b",
      "type": "ollama",
      "base_url": "http://localhost:11434",
      "model": "llama3:8b",
      "parameters": {"temperature": 0.2, "top_p": 0.9, "num_predict": 512}
    }
    ```
  - HTTP genérico:
    ```json
    {
      "name": "generic_http_agent",
      "type": "http",
      "base_url": "http://localhost:8000/v1/chat/completions",
      "headers": {"Authorization": "Bearer CHANGE_ME"},
      "parameters": {"model": "local-model", "temperature": 0.2}
    }
    ```
    Nota: si tu API usa esquema “messages” (estilo OpenAI), adapta `HttpAgent` o pídenos que agreguemos un adaptador dedicado.
  - CLI local:
    ```json
    {
      "name": "cli_local_agent",
      "type": "cli",
      "cmd": "python",
      "args": ["-c", "print(input())"],
      "prompt_stdin": true
    }
    ```
- `rubrics.weights` y `rubrics.thresholds`:
  - Pesos del score final: exactitud, completitud, relevancia, claridad, formato, penalización por tiempo.
  - Umbrales: `aprobado` y `excelente` (por defecto 0.70 y 0.90).

6) Escenarios y casos de prueba
- Estructura general de `scenarios/*.json`:
  ```json
  {
    "name": "mi_escenario",
    "description": "...",
    "cases": [
      {
        "id": "caso_1",
        "prompt": "tu prompt",
        "expected": {
          "must_include": ["palabra"],
          "must_not_include": ["prohibida"],
          "format": {"max_tokens": 10, "list": true, "min_items": 3, "json": false},
          "exact_match_any": ["OK", "APROBADO"]
        }
      }
    ]
  }
  ```
- Campos de expected:
  - `must_include` / `must_not_include`: comprobación de palabras/fragmentos.
  - `format.max_tokens`: máximo de tokens básicos (split por espacios).
  - `format.list` + `format.min_items`: exige formato de lista con “- ”.
  - `format.json` + `required_keys`: exige JSON parseable y presencia de claves.
  - `exact_match_any`: hace pasar exactitud con coincidencia exacta.

7) Ejecución
- Desde la carpeta `tests-cualfication-llm`:
  ```powershell
  python run_tests.py
  ```
- Salida esperada:
  - Se escriben logs por iteración en `logs/` con nombre:
    `<agente>__<timestamp>__iter-<N>__<escenario>__<case>.log`
  - Se generan:
    - `reports/raw_results__<timestamp>.json`
    - `reports/summary__<timestamp>.json`
    - `reports/summary__<timestamp>.md`
    - `reports/summary__<timestamp>.csv`

8) Interpretación de resultados
- Registro crudo por iteración (en raw_results y logs) incluye:
  - `timestamp`, `agent`, `scenario`, `case_id`, `iteration`.
  - `elapsed_s` (latencia), `ok`/`error`.
  - `response`, `response_tokens`, `response_chars`.
  - Medidas: `measures` (exactitud, completitud, relevancia, claridad, formato).
  - `kw`, `fmt`, `exact_match`, `qual`.
  - `final_score` [0..1], `grade` ∈ {insuficiente, aprobado, excelente}.
- Resumen (summary JSON/MD/CSV):
  - `overall`, `by_agent`, `by_scenario`, `by_agent_case`.
  - Latencia: p50/p95/avg/std.
  - Throughput: `throughput_rps` (req/seg), calculado como count/tiempo_total.
  - Score: promedio y desviación.
  - Respuesta: promedios de tokens y chars.
  - Calificaciones: conteo de excelente/aprobado/insuficiente.

9) Ajuste de rúbrica y thresholds
- Edita `config/config.json` en `rubrics.weights` y `rubrics.thresholds`.
- Recomendaciones:
  - Aumenta `exactitud` y `formato` para QA factual y checks duros.
  - Ajusta `penalizacion_tiempo` según criticidad de latencia.
  - Define `aprobado` y `excelente` según tus SLAs.

10) Concurrencia y rendimiento
- `concurrency` controla hilos en paralelo (por defecto 1).
- Aumentar concurrencia acelera pruebas, pero puede afectar a throughput real si el backend es monohilo o comparte GPU.
- Ajusta `timeout_seconds` si hay modelos más lentos.

11) Añadir un nuevo agente
- Crear clase que extienda `BaseAgent` en `src/agents/` e implemente:
  ```python
  def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
      return {"ok": bool, "response": str|None, "error": str|None, "raw": Any}
  ```
- Registrar el tipo en `AGENT_TYPES` (archivo `src/core/orchestrator.py`).
- Añadir configuración del agente en `config/config.json`.

12) Añadir nuevas métricas
- Implementar funciones en `src/metrics/metrics.py`.
- Integrarlas en `Orchestrator._run_single` ajustando `measures` y el cálculo de `final_score`.

13) Buenas prácticas
- Mantén escenarios separados por dominio: `scenarios/qa_*.json`, `scenarios/format_*.json`, etc.
- Usa `must_not_include` para penalizar fugas de información o contenido prohibido.
- Documenta en el escenario lo que consideras éxito y fracaso.

14) Solución de problemas (FAQ)
- Ollama no responde (puerto 11434): asegúrate de que Ollama está corriendo y el modelo descargado (`ollama run llama3:8b`).
- HTTP 401/404: revisa `base_url` y `headers.Authorization`.
- CLI no encuentra el comando: revisa `cmd` y variables de entorno PATH.
- Timeout: aumenta `timeout_seconds` o baja `concurrency`.
- Logs con nombres extraños en Windows: se normalizan con `safe_filename`. Si ves `_`, proviene de caracteres no válidos.
- Respuesta muy larga: usa `format.max_tokens` para restringir, o limita la generación en parámetros del agente.

15) Roadmap (opcional)
- Adaptador HTTP estilo OpenAI (messages) y parsing específico.
- Métricas semánticas (BLEU/ROUGE/BERTScore) si se aceptan dependencias externas.
- Evaluación con LLM juez local para calidad avanzada.
- UI ligera (por ejemplo, Streamlit) para inspección interactiva.

16) Mantenimiento
- Limpieza de artefactos:
  - `logs/` y `reports/` pueden crecer rápidamente. Elimina campañas antiguas según tus políticas.
- Control de versiones: no se hacen commits automáticos; integra esta carpeta a tu VCS si quieres auditar cambios.

17) Comandos útiles
- Ejecutar pruebas (Windows PowerShell):
  ```powershell
  cd "C:\Users\lagreda\Desktop\SISCOM AI AGENT SYSTEM\SISCOM AI AGENT SYSTEM\tests-cualfication-llm"
  python run_tests.py
  ```
- Ver resultados:
  - `reports/summary__<timestamp>.md`
  - `reports/summary__<timestamp>.json`
  - `reports/summary__<timestamp>.csv`

Si necesitas adaptar el agente HTTP a un esquema específico o crear escenarios de tu dominio, indícanos el formato y los incorporamos de inmediato.
