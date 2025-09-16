# Ejecución en entorno aislado con Docker

Este proyecto incluye un Dockerfile y docker-compose.yml para ejecutar las pruebas en un contenedor aislado.

1) Preparación
- Instala Docker Desktop (Windows) o Docker Engine (Linux/Mac).
- Abre una terminal en `tests-cualfication-llm/`.

2) Configurar conectividad a tus backends
- Si usas Ollama o un endpoint HTTP local corriendo en el host, necesitas exponerlo al contenedor.
  - Opción simple: en Windows/Mac, los servicios del host son accesibles como `http://host.docker.internal:<puerto>`.
  - Ajusta `config/config.json` con base_url apropiada (por ejemplo, `http://host.docker.internal:11434` para Ollama).
  - O usa variables de entorno y referéncialas desde el config si prefieres.

3) Construir la imagen
```bash
cd tests-cualfication-llm
docker build -t local/llm-tests:latest .
```

4) Ejecutar con docker-compose
```bash
docker compose up --build
```
- Los artefactos se guardarán en el host:
  - `logs/` y `reports/` en tu carpeta `tests-cualfication-llm`.

5) Personalizaciones
- Montaje de volúmenes ya mapea `config/` y `scenarios/` como solo lectura, y `logs/` y `reports/` como escritura.
- Para usar puertos del host desde el contenedor, descomenta en docker-compose:
  ```yaml
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```
- Cambia `config/config.json` para apuntar a tus backends (ej. Ollama, HTTP). Ejemplo:
  ```json
  {
    "agents": [
      {
        "name": "ollama_llama3_8b",
        "type": "ollama",
        "base_url": "http://host.docker.internal:11434",
        "model": "llama3:8b",
        "parameters": {"temperature": 0.2, "top_p": 0.9, "num_predict": 256}
      }
    ]
  }
  ```

6) Ejecutar con configuración alternativa
- Puedes empaquetar una config distinta y pasarla como argumento:
  ```bash
  docker run --rm -v %cd%/config:/app/config:ro -v %cd%/scenarios:/app/scenarios:ro -v %cd%/logs:/app/logs -v %cd%/reports:/app/reports local/llm-tests:latest python run_tests.py --config /app/config/config.json
  ```
  En PowerShell usa $PWD en lugar de %cd%.

7) Limpieza
- Detén y elimina contenedores con:
  ```bash
  docker compose down
  ```
- Elimina la imagen si es necesario:
  ```bash
  docker rmi local/llm-tests:latest
  ```

8) Notas
- El contenedor no incluye Ollama ni otros backends; se asume que corren fuera y el contenedor se conecta vía red.
- Si necesitas levantar un stack que incluya Ollama u otros servidores dentro de la misma red de docker-compose, se puede añadir como servicio y configurar dependencias.
