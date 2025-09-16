# Propuesta Arquitectónica – Sistema de Testing Avanzado para LLMs Locales

Meta: Diseñar e implementar un sistema profesional, transparente y reproducible para evaluar, comparar y calificar agentes/modelos LLM locales en múltiples escenarios y N iteraciones (≥10), con métricas cualitativas, cuantitativas y calificativas.

1. Capas y módulos
- Capa de Orquestación (src/core)
  - Orchestrator: recorre agentes × escenarios × casos × iteraciones, controla timeouts, registra latencias, reúne resultados.
  - ScenarioLoader: carga escenarios JSON. Cada caso define prompt y criterios esperados.
  - Logger: crea logs por iteración con nombre: <agent>__<timestamp>__iter-<N>__<scenario>__<case>.log
  - Utils: utilidades de tiempo, hashing, serialización.
- Capa de Agentes (src/agents)
  - BaseAgent: interfaz (infer(prompt, timeout)).
  - Adaptadores: OllamaAgent, HttpAgent, CliAgent. Extensible a otros backends locales.
- Capa de Métricas (src/metrics)
  - Métricas cuantitativas: latencia por iteración, longitud de respuesta, ratio de errores.
  - Métricas cualitativas: cobertura de keywords requeridas/prohibidas, checks de formato, exact match.
  - Métricas calificativas: agregación ponderada (rúbrica) incluyendo penalización por SLA.
  - Estadísticos agregados: p50/p95/avg de latencia, score promedio, tasa de éxito.
- Capa de Reportes (src/reporting)
  - Aggregator: resume por agente, por escenario y global.
  - Exporters: JSON y Markdown. (CSV opcional.)

2. Flujo de ejecución
- Leer config/config.json: iteraciones, timeouts, agentes, pesos de rúbrica, dirs.
- Cargar escenarios .json desde scenarios/.
- Para cada agente y cada caso de cada escenario:
  - Ejecutar ≥10 iteraciones.
  - Medir tiempo por solicitud y consolidar métricas de exactitud/completitud/relevancia/claridad/formato.
  - Escribir log único por iteración con parámetros de entrada, tiempos y resultados.
- Persistir resultados crudos y generar resúmenes en reports/.

3. Diseño de escenarios
- Estructura base: { name, description, cases: [{ id, prompt, expected }] }
- expected permite: must_include, must_not_include, format{ max_tokens, list, min_items }, exact_match_any.
- Se pueden crear escenarios por dominios (QA, instrucciones, formato, razonamiento, seguridad) en archivos independientes.

4. Métricas y scoring
- Quant: latencia por iteración, estadísticas p50/p95, longitud respuesta.
- Quali: reglas heurísticas de claridad/estilo; checks de formato/listas; exact match cuando aplique.
- Calificativa: agregación ponderada con pesos en config.rubrics.weights y penalización por demora frente al SLA (timeout_seconds).

5. Logging y trazabilidad
- Nombres de logs: <agent>__<timestamp>__iter-<N>__<scenario>__<case>.log
- Contenido: prompt, respuesta, métricas, latencia, estado (ok/error), datos crudos.
- Transparencia: toda la información requerida para auditoría y repetición.

6. Aislamiento y estructura
- Carpeta dedicada tests-cualfication-llm/ con subcarpetas: config, scenarios, src, logs, reports.
- Sin dependencias externas por defecto; funciona con stdlib. Integración con backends locales vía HTTP/CLI.

7. Extensibilidad y mejores prácticas
- Para nuevos agentes: implementar BaseAgent.infer.
- Para nuevas métricas: añadir funciones en src/metrics y agregarlas en Orchestrator.
- Para más formatos de reporte: implementar en src/reporting/exporters.

8. Ejecución y operación
- Configurar agentes y escenarios.
- Ejecutar run_tests.py.
- Revisar logs y reportes. Usar summary.md/json para comparar agentes.

9. Futuras mejoras (opcionales)
- Paralelización por agente/escenario (ProcessPool/ThreadPool con control de carga).
- Métricas de coherencia semántica (BLEU/ROUGE/BERTScore) si se permiten dependencias opcionales.
- Evaluadores con LLM juez (local) para scoring cualitativo avanzado.
- UI ligera (Streamlit/Gradio) para inspección interactiva.

