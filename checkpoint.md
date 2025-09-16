# Diagnóstico integral del Sistema de Testing y su compatibilidad con el SISCOM AI Agent System

Este documento valida el estado del sistema de testing localizado en `tests-cualfication-llm`, su sinergia con el backend FastAPI y detalla un plan de corrección y adaptación por fases. La validación se basa en revisión estática del código y configuración presentes en el repositorio (no se han ejecutado procesos ni contenedores desde este entorno).

## 1) Resumen ejecutivo

- Estado del framework de testing: sólido, autocontenido, bien documentado, listo para ejecutar smoke-tests por CLI y pruebas con Ollama/HTTP genérico.
- Compatibilidad con el backend actual (FastAPI + LangGraph): parcial.
  - El framework de testing espera endpoints simples de “completion” (prompt → response). El backend expone flujos más complejos (Kafka/Workflows LangGraph, endpoints de negocio) y no un endpoint de “completions” directo.
  - Se recomienda añadir un endpoint auxiliar de “test-completion” en el backend para habilitar pruebas automáticas end-to-end con el sistema de testing actual o, en su defecto, adaptar el `HttpAgent` del sistema de testing para el esquema OpenAI ChatCompletions y exponerlo en el backend.
- Hallazgos clave:
  - Framework OK: diseño limpio, métricas y reporting correctos, Docker funcional, escenarios bien definidos, logging por iteración bien manejado.
  - Riesgo de ruptura con concurrencia > 1: el agregador puede fallar si alguna tarea devuelve un registro de error sin claves mínimas.
  - Sinergia HTTP con el backend: faltan endpoints compatibles o un adaptador dedicado a su API.

## 2) Validación del sistema de testing (`tests-cualfication-llm`)

- Estructura:
  - Orquestador y utilidades: `src/core` (ok)
  - Agentes: `src/agents` (cli, http, ollama) (ok)
  - Métricas: `src/metrics` (latencia p50/p95, score ponderado, checks de formato, cobertura de keywords) (ok)
  - Reporting: JSON/Markdown/CSV (ok)
  - Configuración: `config/config.json` y `config/config.cli.json` (ok)
  - Escenarios: variados (QA, formato, JSON, seguridad) (ok)
  - Docker: `Dockerfile` mínimo con stdlib y docker-compose para host (ok)
- Comportamiento esperado:
  - Logs por iteración en `logs/` con nombres normalizados.
  - Resultados crudos y resúmenes en `reports/`.
  - Operación sin dependencias externas; usa stdlib (urllib, json, concurrent.futures, etc.).
- Robustez:
  - Manejo de timeouts y errores por iteración.
  - Validación de config y escenarios previa a ejecución.

Observaciones puntuales:
- Concurrencia: si `concurrency > 1` y una future falla al resolver, `Orchestrator` añade un registro mínimo `{"ok": False, "error": "..."}` sin claves `agent/scenario/case`; el agregador asume dichos campos y podría lanzar `KeyError`. Con `concurrency=1` (por defecto) no se ve afectado.
- `HttpAgent`: implementa un payload simple `{ "prompt": "..." }`; extrae la respuesta de múltiples formas (`response`, OpenAI-like `choices[0].message.content`, `text` o raw). Se puede extender con un flag `schema=openai` para generar payload estilo ChatCompletions.

## 3) Compatibilidad y sinergia con el backend (FastAPI)

- Backend actual expone endpoints orientados a flujos con Kafka y workflows:
  - `/v1/chat` (produce a Kafka)
  - `/v1/generate-topic-suggestions` (workflow)
  - `/v1/generate-message-suggestion` (workflow)
  - `/v1/generate-room-suggestion` (Kafka)
  - `/v1/role-creation-wizard` (workflow)
  - `/v1/feedback/{run_id}` (Langfuse)
- El sistema de testing necesita un endpoint de inferencia directa tipo “completion” (request con `prompt` → `response` text in-place).
- Conclusión: no existe hoy un endpoint de “completion” directo compatible; por ello:
  - O bien se añade un endpoint auxiliar `/v1/test-completion` (recomendado) que invoque `LLMManager` y devuelva `{ "response": "..." }`.
  - O se extiende `HttpAgent` para soportar un formato `openai/messages` y se añade en el backend un endpoint compatible con ese esquema.

## 4) Problemas detectados y severidad

Críticos:
- Incompatibilidad HTTP directa: falta endpoint de `completion` en el backend para que el `http_agent` realice pruebas end-to-end. Impacto: no se puede testear el backend con este framework sin adaptaciones (bloqueante).
- Concurrencia y agregación: con `concurrency > 1`, posibles errores en aggregator por registros de error sin campos mínimos. Impacto: falla agregación/summary en campañas paralelas (alta).

Medios:
- Config por defecto incluye 3 agentes (ollama/http/cli). Si Ollama/HTTP no están levantados, verás errores y métricas sesgadas. Solución: usar `config.cli.json` o deshabilitar agentes no disponibles.

Bajos:
- `HttpAgent` no tiene modo explícito “openai/messages” aunque intenta deserializar ese formato en la respuesta. Ampliación recomendada para robustez.
- Documentación: ya es buena, pero conviene añadir guía rápida para “endpoint auxiliar de test” y ejemplo de config apuntando al backend.

## 5) Recomendaciones técnicas inmediatas

- Añadir un endpoint auxiliar en el backend para pruebas de completion con `LLMManager` (simple, no intrusivo).
- Endurecer el agregador frente a registros incompletos (mejora de resiliencia con concurrencia).
- Extender `HttpAgent` con `schema=openai` para soportar payload `messages` de ChatCompletions cuando sea necesario.
- Ajustar `config/config.json` para el contexto real (activar solo agentes disponibles o separar perfiles de ejecución).

## 6) Propuestas de cambios (patches sugeridos)

1) Resiliencia del agregador frente a errores con concurrencia

Archivo: `tests-cualfication-llm/src/reporting/aggregator.py`

Propuesta: usar claves con `get()` y defaults para evitar `KeyError`.

```diff
@@
-    for r in run_records:
-        by_agent[r['agent']].append(r)
-        by_scenario[r['scenario']].append(r)
-        by_agent_case[(r['agent'], r['scenario'], r['case_id'])].append(r)
+    for r in run_records:
+        a = r.get('agent', '__unknown__')
+        s = r.get('scenario', '__unknown__')
+        c = r.get('case_id', '__unknown__')
+        by_agent[a].append(r)
+        by_scenario[s].append(r)
+        by_agent_case[(a, s, c)].append(r)
```

2) Extender `HttpAgent` con soporte `schema=openai` (opcional, recomendado)

Archivo: `tests-cualfication-llm/src/agents/http_agent.py`

Idea: soportar dos esquemas:
- `schema: "simple"` (actual, default) → payload `{ "prompt": "...", ... }`
- `schema: "openai"` → payload `{ "model": "...", "messages": [{"role":"user","content": prompt}], ... }`

```diff
@@
 class HttpAgent(BaseAgent):
     def infer(self, prompt: str, timeout: float) -> Dict[str, Any]:
         base_url = self.config.get("base_url")
         headers = self.config.get("headers", {})
         params = self.config.get("parameters", {})
+        schema = self.config.get("schema", "simple")
         if not base_url:
             return {"ok": False, "error": "base_url no configurado"}
-        payload = {"prompt": prompt, **params}
+        if schema == "openai":
+            model = params.get("model", "local-model")
+            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}
+            # Opcional: hyperparams conocidos
+            for k in ("temperature", "top_p", "max_tokens"):
+                if k in params:
+                    payload[k] = params[k]
+        else:
+            payload = {"prompt": prompt, **params}
         data = json.dumps(payload).encode("utf-8")
         req = urllib.request.Request(base_url, data=data, headers={"Content-Type": "application/json", **headers})
         try:
             with urllib.request.urlopen(req, timeout=timeout) as resp:
                 raw_text = resp.read().decode("utf-8")
```

3) Endpoint auxiliar de completion en el backend (recomendado para compatibilidad inmediata)

Archivo: `backend/controllers/agent.py`

Añadir:

```python
from services.llm_manager import LLMManager
from langchain_core.prompts import ChatPromptTemplate

@router.post("/test-completion", summary="Simple LLM completion for testing")
async def test_completion(payload: dict = Body(...)) -> dict:
    """
    Devuelve una inferencia directa del LLM a partir de 'prompt'.
    Compatible con el HttpAgent del sistema de testing.
    """
    prompt = payload.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Campo 'prompt' requerido")

    llm = LLMManager(settings.LLM_MODEL_NAME)
    template = ChatPromptTemplate.from_messages([("user", "{prompt}")])
    try:
        text = await llm.ainvoke(template, prompt=prompt)
        return {"response": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")
```

Nueva configuración de agente (ejemplo) para tests:

```json
{
  "name": "backend_http_completion",
  "type": "http",
  "base_url": "http://localhost:8001/v1/test-completion",
  "parameters": {"temperature": 0.2}
}
```

4) Configuración por perfiles de ejecución

- Para smoke-test local (sin dependencias externas), usar `config/config.cli.json` (CLI agent únicamente).
- Para backend: crea un `config/config.backend.json` con el agente `backend_http_completion` y apúntalo al puerto que expone tu FastAPI.

## 7) Plan de ejecución recomendado (qué y cómo probar)

- Smoke-test CLI (independiente del backend):
  - PowerShell:
    - `cd tests-cualfication-llm`
    - `python run_tests.py --config config\config.cli.json`
  - Docker:
    - `cd tests-cualfication-llm`
    - `docker compose -f docker-compose.cli.yml up --build`

- Prueba contra backend (tras añadir `/v1/test-completion`):
  - Ajusta `tests-cualfication-llm/config/config.json` para incluir el agente `backend_http_completion` y desactiva los que no estén levantados.
  - Ejecuta:
    - `cd tests-cualfication-llm`
    - `python run_tests.py`

- Verifica artefactos:
  - `logs/`: archivos por iteración
  - `reports/`: `summary__<timestamp>.{md,json,csv}` y `raw_results__<timestamp>.json`

Nota: esta guía asume ejecución en tu máquina. Desde este entorno no se han podido correr comandos.

## 8) Roadmap detallado por fases y etapas

Fase 0 – Validación base y smoke CLI (0.5 día)
- Objetivo: garantizar que el framework de testing está íntegro.
- Tareas:
  - Ejecutar smoke-test CLI con `docker-compose.cli.yml` y/o Python local.
  - Confirmar generación de logs y reportes.
- Criterio de éxito: summary en MD/JSON/CSV generados correctamente; tasas de éxito altas en `cli_echo`.

Fase 1 – Compatibilidad HTTP mínima con backend (1 día)
- Objetivo: pruebas end-to-end contra el backend.
- Tareas:
  - Implementar endpoint `/v1/test-completion` (patch 3).
  - Extender `HttpAgent` con `schema=openai` (patch 2, opcional).
  - Configurar un agente `http` apuntando a `/v1/test-completion`.
  - Ejecutar campañas con escenarios básicos (`demo_basic`, `format_and_json`).
- Criterio de éxito: reportes correctos, latencias razonables, score promedio ≥ 0.7 en escenarios simples.

Fase 2 – Robustez y resistencia a errores (0.5–1 día)
- Objetivo: permitir `concurrency > 1` sin romper agregación.
- Tareas:
  - Aplicar patch 1 del agregador.
  - Ejecutar pruebas con `concurrency=4` y verificar que el resumen se genera sin fallos.
- Criterio de éxito: sin `KeyError`; summary generado con datos agregados; throughput incrementa.

Fase 3 – Cobertura de escenarios y guardrails (1–2 días)
- Objetivo: ampliar escenarios que reflejen casos reales del backend (instrucciones, seguridad/safety, formato JSON).
- Tareas:
  - Ajustar/crear escenarios más cercanos a intents del backend (p.ej., respuestas en español controladas, JSON con claves requeridas).
  - Integrar keywords de compliance (`must_not_include`) y checks de formato.
- Criterio de éxito: escenarios nuevos pasan con score ≥ umbral definido; safety y formato respetados.

Fase 4 – Integración CI/CD y Docker (1–2 días)
- Objetivo: automatizar pruebas en pipeline.
- Tareas:
  - Añadir job en CI para construir imagen de tests y ejecutar `run_tests.py`.
  - Publicar artefactos (reports) como outputs del pipeline.
  - Opcional: levantar backend en red de compose y apuntar el test via `host.docker.internal` si aplica.
- Criterio de éxito: pipeline verde con artefactos disponibles; fácil trazabilidad.

Fase 5 – Métricas avanzadas y evaluación “juez” (opcional, 2–4 días)
- Objetivo: evaluación semántica y de calidad avanzada.
- Tareas:
  - Incorporar BLEU/ROUGE/BERTScore (si aceptable añadir dependencias).
  - Agregar un LLM juez local, con prompts de evaluación y rúbrica de mayor fidelidad.
- Criterio de éxito: métricas adicionales en summary con correlación cualitativa útil.

## 9) Checklist de aceptación

- [ ] Ejecuta smoke CLI y valida reports.
- [ ] Implementa `/v1/test-completion` en backend y valida respuesta con curl/postman.
- [ ] Ejecuta pruebas HTTP con el sistema de testing.
- [ ] Aplica fix de agregación y valida `concurrency > 1`.
- [ ] Amplía escenarios y ajusta rúbricas/thresholds según SLAs.
- [ ] Integra a CI/CD.

## 10) Riesgos y mitigaciones

- Backend no expone endpoint “completion”: añadir `/v1/test-completion` o adaptar `HttpAgent` `schema=openai` y crear route compatible.
- Métricas vs. latencia real: el sistema penaliza latencia más allá del SLA; ajusta `rubrics.weights["penalizacion_tiempo"]` según objetivos.
- Errores por endpoints externos: usar smoke CLI y Ollama como pruebas de aislación.

## 11) Conclusión

- El sistema de testing está bien diseñado y listo para ser operativo de inmediato vía CLI y Ollama.
- Para sinergia total con el backend FastAPI, se recomienda:
  - Añadir el endpoint auxiliar de completion (`/v1/test-completion`) o exponer un endpoint estilo ChatCompletions.
  - Aplicar el fix de agregación para soportar concurrencia.
- Con estas acciones, podrás ejecutar campañas de evaluación cuantitativa/cualitativa y obtener reportes útiles para gobernanza y SLAs.

¿Deseas que aplique los parches propuestos directamente en los archivos o prefieres que te prepare un PR con estos cambios? También puedo preparar las configs específicas para tu entorno (puertos y endpoints) y una guía paso a paso de ejecución en tu máquina.
