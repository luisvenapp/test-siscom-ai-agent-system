Guía rápida de evaluación y ajuste de pesos

- exactitud: coincidencia exacta o cobertura de claves requeridas. Recomendado alto peso para QA factual.
- completitud: porcentaje de must_include presentes.
- relevancia: penaliza presencia de must_not_include.
- claridad: heurística de legibilidad (longitud media de oración). Sustituible por evaluadores locales.
- formato: cumplimiento de restricciones (máx tokens, lista, JSON válido, claves requeridas).
- penalizacion_tiempo: factor negativo con base en SLA (timeout_seconds). Ajusta según criticidad de latencia.

Umbrales sugeridos:
- aprobado >= 0.70
- excelente >= 0.90

