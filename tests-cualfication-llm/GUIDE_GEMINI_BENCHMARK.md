# Guía de Ejecución – Benchmark completo de modelos Gemini (Google AI Studio)

Esta guía te lleva paso a paso para ejecutar el benchmark de los modelos de Gemini usando el framework de testing en `tests-cualfication-llm`.

Modelos cubiertos en el preset:
- gemini-2.5-flash
- gemini-2.5-pro
- gemini-2.0-flash
- gemini-2.0-pro

La ejecución es secuencial por modelo (uno por uno) y con reintentos automáticos si un modelo no está disponible.

---

## 1) Prerrequisitos

- Acceso a Internet.
- Python 3.10+ (si ejecutarás localmente) o Docker Desktop (si usarás contenedor).
- Una API Key válida de Google AI Studio (no Vertex AI). Crea tu API Key desde: https://aistudio.google.com/app/apikey

---

## 2) Ubicación de archivos relevantes

- Config de benchmark (Gemini):
  - `tests-cualfication-llm/config/config.benchmark.gemini.json`
- Script PowerShell de ejecución rápida (Windows):
  - `tests-cualfication-llm/scripts/run_benchmark_gemini.ps1`
- Agente Gemini (implementación HTTP):
  - `tests-cualfication-llm/src/agents/gemini_agent.py`
- Directorios de artefactos:
  - Logs por iteración: `tests-cualfication-llm/logs/`
  - Reportes agregados: `tests-cualfication-llm/reports/`

---

## 3) Variables de entorno (recomendado)

Debes exponer tu API Key como variable de entorno para que el agente la utilice.

- Windows PowerShell:
  - `setx GOOGLE_API_KEY "TU_API_KEY"`
  - Cierra y reabre la ventana de PowerShell para que la variable esté disponible.
  - Alternativamente, en la sesión actual: `$env:GOOGLE_API_KEY = "TU_API_KEY"`

- Linux/Mac (bash/zsh):
  - `export GOOGLE_API_KEY="TU_API_KEY"`

Notas:
- El agente Gemini también soporta poner `api_key` en el archivo de configuración (no recomendado por seguridad). Si quisieras hacerlo, podrías editar cada agente y poner: `"api_key": "${GOOGLE_API_KEY}"` para que se expanda desde entorno.

---

## 4) Ejecución local con Python

1) Abre una terminal en el proyecto y ve a la carpeta de tests:
   - Windows PowerShell:
     ```powershell
     cd "C:\Users\lagreda\Desktop\SISCOM AI AGENT SYSTEM\SISCOM AI AGENT SYSTEM\tests-cualfication-llm"
     ```
   - Linux/Mac:
     ```bash
     cd "tests-cualfication-llm"
     ```

2) Verifica que la variable está disponible:
   - PowerShell:
     ```powershell
     echo $env:GOOGLE_API_KEY
     ```
   - Bash/Zsh:
     ```bash
     echo $GOOGLE_API_KEY
     ```

3) Ejecuta el benchmark:
   - PowerShell:
     ```powershell
     python run_tests.py --config config\config.benchmark.gemini.json
     ```
   - Bash/Zsh:
     ```bash
     python3 run_tests.py --config config/config.benchmark.gemini.json
     ```

---

## 5) Ejecución rápida (Windows) con script PowerShell

- Desde `tests-cualfication-llm` puedes usar:
  ```powershell
  ./scripts/run_benchmark_gemini.ps1
  ```

Este script ejecuta el mismo comando Python con el preset de Gemini.

---

## 6) Ejecución con Docker (opcional)

1) Construye la imagen de tests:
   ```bash
   cd tests-cualfication-llm
   docker build -t local/llm-tests:latest .
   ```

2) Ejecuta pasando el config y la API Key por entorno:
   - Linux/Mac (bash):
     ```bash
     docker run --rm \
       -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
       -v $PWD/config:/app/config:ro \
       -v $PWD/scenarios:/app/scenarios:ro \
       -v $PWD/logs:/app/logs \
       -v $PWD/reports:/app/reports \
       local/llm-tests:latest \
       python run_tests.py --config /app/config/config.benchmark.gemini.json
     ```
   - Windows PowerShell:
     ```powershell
     docker run --rm \
       -e GOOGLE_API_KEY=$Env:GOOGLE_API_KEY \
       -v ${PWD}/config:/app/config:ro \
       -v ${PWD}/scenarios:/app/scenarios:ro \
       -v ${PWD}/logs:/app/logs \
       -v ${PWD}/reports:/app/reports \
       local/llm-tests:latest \
       python run_tests.py --config /app/config/config.benchmark.gemini.json
     ```

---

## 7) Qué hace el preset de Gemini

- `config/config.benchmark.gemini.json` define:
  - `agent_execution: "sequential"` (ejecución modelo por modelo)
  - `within_agent_concurrency: 1`
  - `max_model_fail_retries: 2` (2 reintentos si un modelo falla; luego salta al siguiente)
  - Modelos a evaluar:
    - gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash, gemini-2.0-pro

- Métricas y reporte:
  - Latencia p50/p95/avg/std y throughput.
  - Puntaje final compuesto según rúbrica.
  - Resumen por agente (modelo) y global.
  - Sección de “Benchmark entre modelos (por agente)” en el MD con score y latencias comparadas.

---

## 8) Dónde ver los resultados

- Logs por iteración (útiles para debug):
  - `tests-cualfication-llm/logs/`
  - Formato de nombres: `<agente>__<timestamp>__iter-<N>__<escenario>__<case>.log`

- Reportes agregados:
  - `tests-cualfication-llm/reports/summary__<timestamp>.md` (recomendado)
  - `tests-cualfication-llm/reports/summary__<timestamp>.json`
  - `tests-cualfication-llm/reports/summary__<timestamp>.csv`

---

## 9) Ajustes útiles para Gemini

Puedes ajustar parámetros en `config/config.benchmark.gemini.json` dentro de `parameters` de cada agente:
- `temperature`, `top_p` (topP), `top_k` (topK), `max_tokens` (maxOutputTokens)
- `system_instruction`: añade una instrucción de sistema (por ejemplo: "Responde en español con 2 oraciones...")
- `stop_sequences`: lista de secuencias de parada
- `candidate_count`: número de candidatos a pedir (cuidado: afecta latencia y cuotas)
- `safety_settings`: lista de reglas para contenido seguro (ver docs de Google AI Studio)

Ejemplo de agente con instrucciones de sistema y top_p:
```json
{
  "name": "gemini_25_flash",
  "type": "gemini",
  "model": "gemini-2.5-flash",
  "parameters": {
    "temperature": 0.2,
    "top_p": 0.95,
    "system_instruction": "Responde en español, formato breve y claro."
  }
}
```

---

## 10) Solución de problemas

- 401/403 Unauthorized:
  - Asegúrate de que `GOOGLE_API_KEY` está presente y vigente.
  - Verifica que la cuenta y el proyecto tienen acceso al modelo indicado.

- 400 Bad Request (modelo incorrecto):
  - Revisa el nombre exacto del modelo (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-2.0-pro`).

- 429 Too Many Requests (cuotas):
  - Disminuye `iterations`, sube `timeout_seconds`, o ejecuta en horarios con menos tráfico.

- Tiempo de espera (timeout):
  - Aumenta `timeout_seconds` en la configuración (ej. 180).

- Contenido bloqueado:
  - El agente registra `blockReason` cuando la API lo informa. Ajusta prompts, safety settings o escenarios.

- Proxy/cortafuegos corporativo:
  - Verifica conectividad hacia `https://generativelanguage.googleapis.com`.

---

## 11) Interpretación del resumen (MD)

La sección "Benchmark entre modelos (por agente)" lista cada modelo con:
- `score_avg`: promedio del puntaje compuesto (mayor es mejor)
- `lat_avg`: latencia promedio (menor es mejor)
- `ok`: tasa de éxito
- `throughput`: peticiones/segundo (mayor es mejor)

Usa esta información para:
- Elegir el modelo más balanceado entre calidad y latencia.
- Ajustar parámetros (p. ej., `temperature`, `top_p`) y volver a correr.

---

## 12) Siguientes pasos

- Ejecutar el preset mixto para comparar Gemini vs OpenAI vs DeepSeek vs Ollama:
  ```powershell
  ./scripts/run_benchmark_mixed.ps1
  ```
- Ajustar escenarios (`tests-cualfication-llm/scenarios/*.json`) para tu dominio.
- Integración en CI/CD: crear un job que ejecute el benchmark y publique `reports/summary__*.md` como artefacto.

---

¿Necesitas que agreguemos un preset con instrucciones de sistema estandarizadas en todos los modelos Gemini (ej. idioma, concisión, formato JSON)? Indícame la política deseada y lo preparo de inmediato.
