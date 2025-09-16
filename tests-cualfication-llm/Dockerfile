# Imagen base ligera con Python 3.11
FROM python:3.11-slim

# Evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive

# Crear directorio de trabajo
WORKDIR /app

# Copiar únicamente el runner y código fuente
COPY ./src ./src
COPY ./config ./config
COPY ./scenarios ./scenarios
COPY ./run_tests.py ./run_tests.py

# Crear directorios para artefactos
RUN mkdir -p logs reports

# Comando por defecto: ejecutar pruebas
CMD ["python", "run_tests.py"]
