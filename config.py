"""
config.py
Configuración del simulador de inscripción.

Los archivos de datos NO se incluyen en el repositorio de GitHub.
Se suben como "Secret Files" en el dashboard de Render y se montan
automáticamente en /etc/secrets/ dentro del servidor.

Para desarrollo local, coloca los archivos en la carpeta data/ del proyecto.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# En Render los Secret Files se montan en /etc/secrets/
# En local se leen desde data/ (no se sube a GitHub)
if os.path.exists("/etc/secrets"):
    DATA_DIR = "/etc/secrets"
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")

# ── Archivos de datos ─────────────────────────────────────────────────────────
ARCHIVO_ALUMNOS      = os.path.join(DATA_DIR, "selecciones.json")
ARCHIVO_PROGRAMACION = os.path.join(DATA_DIR, "programacion.csv")
ARCHIVO_PLANES       = os.path.join(DATA_DIR, "planes.json")   # opcional

# ── Parámetros de simulación ──────────────────────────────────────────────────
SEED       = 42
N_CORRIDAS = 15
