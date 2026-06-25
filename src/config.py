"""
Configuración global de rutas y parámetros del proyecto FocCAST.
"""
import os

# --- RUTAS DEL SISTEMA ---
# Obtiene la raíz del proyecto (directorio donde está src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directorios de datos
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DATA_RAW = os.path.join(DATA_DIR, "raw")
DATA_PROCESSED = os.path.join(DATA_DIR, "processed")

# Directorio de salidas (logs, gráficas, resultados)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")

# Directorio de recursos GUI
GUI_RESOURCES = os.path.join(PROJECT_ROOT, "src", "gui", "resources")

# --- PARÁMETROS POR DEFECTO DEL MODELO ---
DEFAULT_GRID_SIZE = 500  # metros por celda

# Estados (para usar en todo el código)
STATE_GREEN = 0
STATE_RECOVERY = 1
STATE_BURNED = 2
STATE_POPULATION = 3

# Diccionario para mapear estados a colores (RGB)
STATE_COLORS = {
    STATE_GREEN: (34, 139, 34),    # ForestGreen
    STATE_RECOVERY: (255, 165, 0), # Orange
    STATE_BURNED: (255, 0, 0),     # Red
    STATE_POPULATION: (128, 128, 128) # Gray
}