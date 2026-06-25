#!/usr/bin/env python3
"""
Script de inicialización del proyecto FocCAST.
Ejecutar desde la raíz del proyecto con: python scripts/setup_structure.py
Crea todas las carpetas y archivos placeholder necesarios.
"""

import os
import sys

def create_project_structure():
    # Obtener la raíz del proyecto (directorio padre de 'scripts')
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # Cambiar al directorio raíz para que las rutas relativas funcionen bien
    os.chdir(project_root)
    print(f"📁 Configurando estructura del proyecto en: {project_root}\n")

    # --------------------------------------------
    # 1. DEFINICIÓN DE CARPETAS
    # --------------------------------------------
    folders = [
        "docs",
        "tests",
        "src/core",
        "src/data/spain",
        "src/data/adapters",
        "src/gui/resources/css",
        "src/gui/resources/js",
        "src/utils",
        "src/resources/icons",
        "data/raw",          # Para descargas brutas (shapefiles, GeoTIFFs)
        "data/processed",    # Para arrays .npy preprocesados
        "outputs",           # Para resultados de simulaciones y gráficas
    ]

    for folder in folders:
        path = os.path.join(project_root, folder)
        os.makedirs(path, exist_ok=True)
        print(f"   ✅ Carpeta creada/verificada: {folder}")

    # --------------------------------------------
    # 2. DEFINICIÓN DE ARCHIVOS (con contenido inicial)
    # --------------------------------------------
    files_content = {
        # --- RAÍZ ---
        "README.md": "# FocCAST\n\nSistema de Predicción de Incendios Forestales con componente antrópica (Autómata Celular Híbrido).\n\n## Estado\n🚧 En desarrollo activo.\n",
        "requirements.txt": "PyQt6>=6.5.0\nnumpy>=1.24.0\ngeopandas>=0.14.0\npandas>=2.0.0\nrasterio>=1.3.0\npillow>=10.0.0\nmatplotlib>=3.7.0\nscipy>=1.11.0\n",
        "pyproject.toml": "[build-system]\nrequires = [\"setuptools>=61.0\"]\nbuild-backend = \"setuptools.build_meta\"\n\n[project]\nname = \"foccast\"\nversion = \"0.1.0\"\ndescription = \"Wildfire prediction system with anthropogenic component\"\n",
        ".gitignore": "__pycache__/\n*.pyc\n*.pyo\n*.npy\n*.geojson\n*.shp\n*.shx\n*.dbf\n*.prj\n*.tif\n.idea/\n.vscode/\ndata/raw/*\ndata/processed/*\noutputs/*\n!data/raw/.gitkeep\n!data/processed/.gitkeep\n!outputs/.gitkeep\n",
        "run.py": "#!/usr/bin/env python3\nimport sys\nfrom src.main import launch\n\nif __name__ == \"__main__\":\n    sys.exit(launch())\n",

        # --- SRC (Raíz del paquete) ---
        "src/__init__.py": "",
        "src/main.py": "\"\"\"Punto de entrada principal de la aplicación desktop.\"\"\"\nimport sys\nfrom PyQt6.QtWidgets import QApplication\nfrom src.gui.main_window import MainWindow\n\ndef launch() -> int:\n    app = QApplication(sys.argv)\n    window = MainWindow()\n    window.show()\n    return app.exec()\n",
        "src/config.py": "\"\"\"Configuración global de rutas y parámetros.\"\"\"\nimport os\n\nPROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\nDATA_RAW = os.path.join(PROJECT_ROOT, \"data\", \"raw\")\nDATA_PROCESSED = os.path.join(PROJECT_ROOT, \"data\", \"processed\")\nOUTPUT_DIR = os.path.join(PROJECT_ROOT, \"outputs\")\n\n# Parámetros por defecto del modelo\nDEFAULT_GRID_SIZE = 500  # metros\n",

        # --- CORE ---
        "src/core/__init__.py": "",
        "src/core/engine.py": "\"\"\"Motor principal del Autómata Celular.\"\"\"\nimport numpy as np\n\nclass FocCASTEngine:\n    def __init__(self, grid_shape):\n        self.grid = np.zeros(grid_shape, dtype=np.int8)\n        print(f\"Engine inicializado con grid {grid_shape}\")\n",
        "src/core/cell_rules.py": "\"\"\"Reglas de transición de estados (V, R, Q, P).\"\"\"\n# Estados: 0=Verde, 1=Recuperación, 2=Quemado, 3=Poblacional\n",
        "src/core/probabilities.py": "\"\"\"Cálculo vectorizado de P_contagio y P_antropico.\"\"\"\n",
        "src/core/parameters.py": "\"\"\"Gestión del vector de parámetros Θ (Theta).\"\"\"\n",

        # --- DATA (Adaptadores) ---
        "src/data/__init__.py": "",
        "src/data/base_loader.py": "\"\"\"Interfaz abstracta para cargadores de datos.\"\"\"\nfrom abc import ABC, abstractmethod\n\nclass BaseLoader(ABC):\n    @abstractmethod\n    def load(self, year: int):\n        pass\n",
        "src/data/spain/__init__.py": "",
        "src/data/spain/fire_loader.py": "\"\"\"Cargador de incendios históricos (EGIF / GVA).\"\"\"\n",
        "src/data/spain/land_loader.py": "\"\"\"Cargador de usos de suelo (CORINE / SIOSE).\"\"\"\n",
        "src/data/spain/urban_loader.py": "\"\"\"Cargador de núcleos urbanos (Catastro / OSM).\"\"\"\n",
        "src/data/spain/meteo_loader.py": "\"\"\"Cargador de datos meteorológicos (AEMET).\"\"\"\n",
        "src/data/spain/dem_loader.py": "\"\"\"Cargador de orografía (MDT-IGN).\"\"\"\n",
        "src/data/spain/population_loader.py": "\"\"\"Cargador de densidad poblacional (INE).\"\"\"\n",
        "src/data/adapters/README.md": "# Adaptadores para otros países\n\nImplementar aquí las clases para Portugal, Francia, etc., siguiendo la interfaz `BaseLoader`.\n",

        # --- GUI ---
        "src/gui/__init__.py": "",
        "src/gui/main_window.py": "\"\"\"Ventana principal de la aplicación.\"\"\"\nfrom PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout\n\nclass MainWindow(QMainWindow):\n    def __init__(self):\n        super().__init__()\n        self.setWindowTitle(\"FocCAST - Predicción de Incendios\")\n        self.setGeometry(100, 100, 1400, 800)\n        \n        central_widget = QWidget()\n        self.setCentralWidget(central_widget)\n        layout = QHBoxLayout(central_widget)\n        \n        # Aquí se añadirán el MapWidget y los paneles laterales\n        print(\"MainWindow inicializada.\")\n",
        "src/gui/map_widget.py": "\"\"\"Widget que incrusta OpenStreetMap vía WebEngine.\"\"\"\nfrom PyQt6.QtWebEngineWidgets import QWebEngineView\n\nclass MapWidget(QWebEngineView):\n    def __init__(self):\n        super().__init__()\n        # Cargará el HTML con Leaflet\n        print(\"MapWidget inicializado.\")\n",
        "src/gui/timeline_control.py": "\"\"\"Widget del slider temporal (línea de tiempo).\"\"\"\n",
        "src/gui/params_panel.py": "\"\"\"Panel de visualización de parámetros Θ y métricas.\"\"\"\n",
        "src/gui/inspector.py": "\"\"\"Panel inferior para inspeccionar celdas al hacer clic.\"\"\"\n",
        "src/gui/resources/map_template.html": "<!DOCTYPE html>\n<html>\n<head>\n    <meta charset='UTF-8'>\n    <title>FocCAST - Mapa Interactivo</title>\n    <link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css' />\n    <script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>\n    <style>\n        body, html, #map { margin: 0; padding: 0; width: 100%; height: 100%; }\n    </style>\n</head>\n<body>\n    <div id='map'></div>\n    <script>\n        var map = L.map('map').setView([40.0, -3.0], 6);\n        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {\n            maxZoom: 19,\n            attribution: '© OpenStreetMap contributors'\n        }).addTo(map);\n        console.log('Mapa OSM cargado correctamente.');\n    </script>\n</body>\n</html>",
        "src/gui/resources/css/custom_style.css": "/* Estilos personalizados para el mapa y controles */",
        "src/gui/resources/js/map_controller.js": "// Controlador JavaScript para la interacción con Python (QWebChannel)\nconsole.log('Map controller loaded.');",

        # --- UTILS ---
        "src/utils/__init__.py": "",
        "src/utils/logger.py": "\"\"\"Configuración de logging para el sistema.\"\"\"\nimport logging\n\ndef setup_logger():\n    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')\n    return logging.getLogger(\"FocCAST\")\n",
        "src/utils/geometry.py": "\"\"\"Cálculos de distancias geodésicas y vecindad de Moore.\"\"\"\n",
        "src/utils/raster_utils.py": "\"\"\"Funciones auxiliares para manejo de GeoTIFFs y arrays.\"\"\"\n",
        "src/utils/validators.py": "\"\"\"Validación de datos de entrada y salida.\"\"\"\n",

        # --- RESOURCES ---
        "src/resources/styles.qss": "/* QSS para la aplicación desktop */\nQMainWindow { background-color: #f0f0f0; }\n",

        # --- TESTS ---
        "tests/__init__.py": "",
        "tests/test_core_engine.py": "import unittest\n\nclass TestEngine(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n",
        "tests/test_probabilities.py": "import unittest\n\nclass TestProbabilities(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n",
        "tests/test_spanish_loaders.py": "import unittest\n\nclass TestSpanishLoaders(unittest.TestCase):\n    def test_placeholder(self):\n        self.assertTrue(True)\n",

        # --- SCRIPTS (además del propio) ---
        "scripts/download_egif.py": "\"\"\"Descarga los datos de incendios del MITECO (EGIF).\"\"\"\nprint(\"Descargando EGIF...\")\n",
        "scripts/download_catastro.py": "\"\"\"Descarga los shapefiles de Catastro por provincia.\"\"\"\nprint(\"Descargando Catastro...\")\n",
        "scripts/build_grid.py": "\"\"\"Construye la malla de 500x500m y asigna usos de suelo.\"\"\"\nimport numpy as np\nprint(\"Construyendo grid base...\")\n",
        "scripts/migrate_data.py": "\"\"\"Migra capas de usos de suelo entre años (1990->2020).\"\"\"\nprint(\"Migrando datos temporales...\")\n",
    }

    # Escribir los archivos
    for rel_path, content in files_content.items():
        full_path = os.path.join(project_root, rel_path)
        # Asegurar que la carpeta del archivo existe
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Escribir el contenido (si el archivo ya existe, NO SOBRESCRIBIR para no perder trabajo)
        if not os.path.exists(full_path):
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   📄 Archivo creado: {rel_path}")
        else:
            print(f"   ⏩ Archivo existente, omitido: {rel_path}")

    # Archivos .gitkeep para mantener carpetas vacías en el repo
    keep_files = ["data/raw/.gitkeep", "data/processed/.gitkeep", "outputs/.gitkeep"]
    for keep in keep_files:
        path = os.path.join(project_root, keep)
        if not os.path.exists(path):
            with open(path, 'w') as f:
                f.write("")  # Vacío
            print(f"   📄 Archivo creado: {keep}")

    print("\n🎉 ¡Estructura del proyecto FocCAST inicializada con éxito!")
    print("👉 Ahora puedes ejecutar: python run.py")
    print("👉 O instalar en modo editable: pip install -e .")

if __name__ == "__main__":
    create_project_structure()