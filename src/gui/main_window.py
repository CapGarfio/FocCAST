# -*- coding: utf-8 -*-
"""
Ventana principal de la aplicacion FocCAST.
Integra el mapa, el motor de simulacion, el control temporal,
selector de provincias y selector de comarcas.
Los contornos se cargan desde archivos locales (sin descargas automaticas).
"""
import sys
import os
import json
import numpy as np
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSlider, QPushButton, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal

from src.config import DATA_PROCESSED, DATA_RAW
from src.gui.map_widget import MapWidget
from src.core.engine import FocCASTEngine
from src.data.spain.provincias import get_province_list, get_province_bbox
from src.data.spain.comarcas import get_comarcas, get_comarca_bbox

# ------------------------------------------------------------
# Worker para generar el grid en segundo plano
# ------------------------------------------------------------
class GridGenerationWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, province_code, bbox, suffix=""):
        super().__init__()
        self.province_code = province_code
        self.bbox = bbox
        self.suffix = suffix

    def run(self):
        try:
            from scripts.build_real_grid import build_grid_from_bbox
            success = build_grid_from_bbox(self.province_code, self.bbox, name_suffix=self.suffix)
            if success:
                self.finished.emit(self.province_code)
            else:
                self.error.emit(f"Error al generar grid para provincia {self.province_code}")
        except Exception as e:
            self.error.emit(str(e))

# ------------------------------------------------------------
# Ventana principal
# ------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocCAST - Prediccion de Incendios Forestales")
        self.setGeometry(50, 50, 1400, 800)

        # --- Estado interno ---
        self.engine = None
        self.current_month = 0
        self.max_months = 60
        self.worker = None

        # --- Widget central y layout principal ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # --- COLUMNA IZQUIERDA: Mapa + Slider ---
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        # 1. Mapa
        self.map_widget = MapWidget(self)
        left_layout.addWidget(self.map_widget, stretch=1)

        # 2. Barra de control temporal (Slider)
        slider_frame = QFrame()
        slider_frame.setFrameShape(QFrame.Shape.StyledPanel)
        slider_frame.setStyleSheet("background-color: #34495e; border-radius: 5px; padding: 5px;")
        slider_layout = QHBoxLayout(slider_frame)

        self.time_slider = QSlider(Qt.Orientation.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(self.max_months)
        self.time_slider.setValue(0)
        self.time_slider.setTickInterval(12)
        self.time_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.time_slider.valueChanged.connect(self.on_slider_change)

        self.slider_label = QLabel("Mes 0")
        self.slider_label.setStyleSheet("color: white; font-weight: bold; min-width: 60px;")

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedWidth(30)
        self.btn_play.clicked.connect(self.toggle_animation)

        slider_layout.addWidget(QLabel("Tiempo:"))
        slider_layout.addWidget(self.time_slider, stretch=1)
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.btn_play)

        left_layout.addWidget(slider_frame)

        # --- COLUMNA DERECHA: Panel de control ---
        right_panel = QWidget()
        right_panel.setFixedWidth(280)
        right_panel.setStyleSheet("background-color: #2c3e50; border-radius: 5px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.setSpacing(15)

        # Titulo
        title_label = QLabel("📊 Panel de Control")
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; padding: 10px;")
        right_layout.addWidget(title_label)

        # Selector de provincia
        right_layout.addWidget(QLabel("Seleccionar provincia:"))
        self.province_combo = QComboBox()
        self.province_combo.setStyleSheet("background-color: white; padding: 5px; border-radius: 3px;")
        for code, name in get_province_list():
            self.province_combo.addItem(f"{code} - {name}", code)
        # Seleccionar Valencia (46) por defecto
        index = self.province_combo.findData("46")
        if index >= 0:
            self.province_combo.setCurrentIndex(index)
        self.province_combo.currentIndexChanged.connect(self.on_province_changed)
        right_layout.addWidget(self.province_combo)

        # Selector de comarca
        right_layout.addWidget(QLabel("Comarca (opcional):"))
        self.comarca_combo = QComboBox()
        self.comarca_combo.setStyleSheet("background-color: white; padding: 5px; border-radius: 3px;")
        self.comarca_combo.addItem("Toda la provincia", None)
        right_layout.addWidget(self.comarca_combo)

        # Boton para cargar provincia
        self.load_btn = QPushButton("📥 Cargar provincia")
        self.load_btn.setStyleSheet("background-color: #2980b9; color: white; padding: 8px; border-radius: 5px;")
        self.load_btn.clicked.connect(self.load_selected_province)
        right_layout.addWidget(self.load_btn)
        
        # Botón para centrar en la provincia actual
        center_btn = QPushButton("📍 Centrar en provincia")
        center_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px; border-radius: 5px;")
        center_btn.clicked.connect(self.center_on_province)
        right_layout.addWidget(center_btn)        

        # Informacion del grid
        self.info_label = QLabel("Estado: Cargando...\nCeldas: -")
        self.info_label.setStyleSheet("color: #ecf0f1; padding: 10px; background-color: #34495e; border-radius: 5px;")
        right_layout.addWidget(self.info_label)

        # Estadisticas de estados
        self.stats_label = QLabel("Verde: 0%\nRecuperacion: 0%\nQuemado: 0%\nPoblacional: 0%")
        self.stats_label.setStyleSheet("color: #ecf0f1; padding: 10px; background-color: #34495e; border-radius: 5px;")
        right_layout.addWidget(self.stats_label)

        # Boton de reinicio
        reset_btn = QPushButton("🔄 Reiniciar simulacion")
        reset_btn.setStyleSheet("background-color: #e67e22; color: white; padding: 8px; border-radius: 5px;")
        reset_btn.clicked.connect(self.reset_simulation)
        right_layout.addWidget(reset_btn)

        # Boton para forzar un incendio (prueba)
        fire_btn = QPushButton("🔥 Ignicion aleatoria")
        fire_btn.setStyleSheet("background-color: #c0392b; color: white; padding: 8px; border-radius: 5px;")
        fire_btn.clicked.connect(self.random_ignition)
        right_layout.addWidget(fire_btn)

        right_layout.addStretch()

        # --- Ensamblar layout principal ---
        main_layout.addWidget(left_column, stretch=4)
        main_layout.addWidget(right_panel, stretch=1)

        # --- Inicializar ---
        self.load_test_grid()

        # Timer para animacion
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animation_step)
        self.animation_running = False

        # Inicializar combo de comarcas con la provincia por defecto
        self.on_province_changed()

    def download_provincias_geojson(self, output_path):
        """
        Descarga el TopoJSON de provincias desde es-atlas y lo convierte a GeoJSON.
        Retorna True si éxito, False si falla.
        """
        import topojson as tp
        import json
        
        url = "https://unpkg.com/es-atlas/es/provinces.json"
        try:
            print(f"Descargando TopoJSON desde: {url}")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                topo_data = response.json()
                # Convertir TopoJSON a GeoJSON
                geojson_data = tp.Topology(topo_data).to_geojson()
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(geojson_data, f, ensure_ascii=False, indent=2)
                print(f"GeoJSON guardado en {output_path}")
                return True
            else:
                print(f"Error descargando TopoJSON: {response.status_code}")
                return False
        except ImportError:
            print("La librería 'topojson' no está instalada. Ejecuta: pip install topojson")
            return False
        except Exception as e:
            print(f"Error en descarga/conversión: {e}")
            return False

    def center_on_province(self):
        """Centra el mapa en la provincia actual (usando el bbox)."""
        province_code = self.province_combo.currentData()
        if not province_code:
            return
        bbox = self.comarca_combo.currentData()
        if bbox is None:
            bbox = get_province_bbox(province_code)
        if bbox:
            bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]
            self.map_widget.center_map(bounds)
            print("📍 Mapa centrado en la provincia.")


    # ------------------------------------------------------------
    # Metodos de carga de datos
    # ------------------------------------------------------------
    def load_test_grid(self):
        """Carga la provincia por defecto (Valencia) al iniciar."""
        index = self.province_combo.findData("46")
        if index >= 0:
            self.province_combo.setCurrentIndex(index)
        self.load_selected_province()

    def on_province_changed(self):
        """Actualiza el combo de comarcas según la provincia seleccionada."""
        province_code = self.province_combo.currentData()
        self.comarca_combo.clear()
        self.comarca_combo.addItem("Toda la provincia", None)
        comarcas = get_comarcas(province_code)
        for name, bbox in comarcas:
            self.comarca_combo.addItem(name, bbox)
        self.comarca_combo.setCurrentIndex(0)

    def load_selected_province(self):
        """Carga la provincia/comarca seleccionada."""
        province_code = self.province_combo.currentData()
        if not province_code:
            return

        bbox = self.comarca_combo.currentData()
        suffix = ""
        if bbox is None:
            bbox = get_province_bbox(province_code)
            if bbox is None:
                self.info_label.setText("Error: bbox no encontrado.")
                return
        else:
            comarca_name = self.comarca_combo.currentText()
            suffix = f"_{comarca_name.replace(' ', '_')}"

        # Deshabilitar controles mientras se carga
        self.province_combo.setEnabled(False)
        self.comarca_combo.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.info_label.setText("Generando grid...")

        self.worker = GridGenerationWorker(province_code, bbox, suffix)
        self.worker.finished.connect(self.on_grid_generated)
        self.worker.error.connect(self.on_grid_error)
        self.worker.start()

    def on_grid_generated(self, province_code):
        self.province_combo.setEnabled(True)
        self.comarca_combo.setEnabled(True)
        self.load_btn.setEnabled(True)

        suffix = ""
        if self.comarca_combo.currentData() is not None:
            comarca_name = self.comarca_combo.currentText()
            suffix = f"_{comarca_name.replace(' ', '_')}"

        grid_path = os.path.join(DATA_PROCESSED, f"grid_{province_code}{suffix}.npy")
        if os.path.exists(grid_path):
            grid_data = np.load(grid_path)
            self.init_engine(grid_data)
            self.update_map()
            
            # --- Centrar mapa en el bbox de la provincia ---
            bbox = self.comarca_combo.currentData()
            if bbox is None:
                bbox = get_province_bbox(province_code)
            if bbox:
                # Leaflet bounds: [[sur, oeste], [norte, este]]
                bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]
                self.map_widget.center_map(bounds)
            
            # Cargar contorno (sin ajustar el zoom)
            self.load_province_contour(province_code, fit_bounds=False)
            self.info_label.setText("Provincia/comarca cargada correctamente.")
        else:
            self.info_label.setText("Error: grid no encontrado.")


    def on_grid_error(self, error_msg):
        self.province_combo.setEnabled(True)
        self.comarca_combo.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.info_label.setText(f"Error: {error_msg}")
        print(f"Error generando grid: {error_msg}")

    def init_engine(self, grid_data):
        self.engine = FocCASTEngine(
            grid_shape=grid_data.shape,
            initial_grid=grid_data,
            tau_rec=6,
            tau_verde=24
        )
        self.current_month = 0
        self.time_slider.setMaximum(self.max_months)
        self.time_slider.setValue(0)
        self.slider_label.setText("Mes 0")
        rows, cols = grid_data.shape
        self.info_label.setText(f"Estado: Simulacion lista\nCeldas: {rows}x{cols}")
        self.update_stats(grid_data)

    # ------------------------------------------------------------
    # Metodo simplificado para cargar contorno desde archivo local
    # ------------------------------------------------------------
    def load_province_contour(self, province_code, fit_bounds=False):
        """
        Carga el contorno de la provincia desde el archivo GeoJSON procesado.
        fit_bounds: si es True, ajusta el zoom al contorno (por defecto False).
        """
        import json
        
        geojson_path = os.path.join(DATA_PROCESSED, "provinces_clean.geojson")
        
        if not os.path.exists(geojson_path):
            print(f"⚠️ Archivo {geojson_path} no encontrado.")
            return
        
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error al leer GeoJSON: {e}")
            return
        
        features = data.get('features', [])
        if not features:
            print("El GeoJSON no contiene features.")
            return
        
        # Obtener nombre de la provincia desde el combo
        idx = self.province_combo.findData(province_code)
        if idx < 0:
            print(f"❌ No se encontró el código {province_code} en el combo.")
            return
        
        provincia_nombre = self.province_combo.itemText(idx).split(" - ")[1] if " - " in self.province_combo.itemText(idx) else None
        if not provincia_nombre:
            print("❌ No se pudo obtener el nombre de la provincia desde el combo.")
            return
        
        # Buscar por nombre
        campo_nombre = 'name'  # Asumimos que el campo se llama 'name'
        print(f"🔍 Buscando '{provincia_nombre}' en campo '{campo_nombre}'...")
        
        filtered = []
        for feature in features:
            props = feature.get('properties', {})
            nombre = props.get(campo_nombre)
            if nombre and provincia_nombre.lower() in nombre.lower():
                filtered.append(feature)
                print(f"✅ Encontrado: {nombre}")
                break
        
        if filtered:
            province_geojson = {"type": "FeatureCollection", "features": filtered}
            # Añadir contorno con el color y grosor deseado, y el fit_bounds según parámetro
            self.map_widget.add_contour(province_geojson, color='#000000', weight=3, fit_bounds=fit_bounds)
            print(f"✅ Contorno de {provincia_nombre} cargado en NEGRO.")
        else:
            print(f"❌ No se encontró la provincia '{provincia_nombre}' en el GeoJSON.")

  
    # ------------------------------------------------------------
    # Metodos de actualizacion del mapa y estadisticas
    # ------------------------------------------------------------
    def update_map(self):
        if self.engine is None:
            return
        grid = self.engine.grid
        self.map_widget.update_grid(grid)
        self.update_stats(grid)

    def update_stats(self, grid):
        unique, counts = np.unique(grid, return_counts=True)
        total = grid.size
        stats = {}
        for st, cnt in zip(unique, counts):
            pct = cnt / total * 100
            name = {0: "Verde", 1: "Recuperacion", 2: "Quemado", 3: "Poblacional"}.get(st, "Desconocido")
            stats[name] = pct
        text = (
            f"Verde: {stats.get('Verde', 0):.1f}%\n"
            f"Recuperacion: {stats.get('Recuperacion', 0):.1f}%\n"
            f"Quemado: {stats.get('Quemado', 0):.1f}%\n"
            f"Poblacional: {stats.get('Poblacional', 0):.1f}%"
        )
        self.stats_label.setText(text)

    # ------------------------------------------------------------
    # Metodos del slider y control temporal
    # ------------------------------------------------------------
    def on_slider_change(self, value):
        self.current_month = value
        self.slider_label.setText(f"Mes {value}")
        if self.engine is not None:
            grid = self.engine.get_grid_at_time(value)
            self.map_widget.update_grid(grid)
            self.update_stats(grid)

    def reset_simulation(self):
        if self.engine is not None and len(self.engine.history) > 0:
            initial_grid = self.engine.history[0]
            self.engine.reset(initial_grid)
            self.current_month = 0
            self.time_slider.setValue(0)
            self.slider_label.setText("Mes 0")
            self.update_map()
            print("Simulacion reiniciada.")

    # ------------------------------------------------------------
    # Metodos de animacion
    # ------------------------------------------------------------
    def toggle_animation(self):
        if self.animation_running:
            self.animation_timer.stop()
            self.btn_play.setText("▶")
            self.animation_running = False
        else:
            if self.current_month >= self.max_months:
                self.reset_simulation()
            self.animation_timer.start(300)
            self.btn_play.setText("⏸")
            self.animation_running = True

    def animation_step(self):
        if self.engine is None:
            self.toggle_animation()
            return
        next_month = self.current_month + 1
        if next_month > self.max_months:
            self.toggle_animation()
            return
        self.time_slider.setValue(next_month)

    # ------------------------------------------------------------
    # Metodo de prueba: ignicion aleatoria
    # ------------------------------------------------------------
    def random_ignition(self):
        if self.engine is None:
            return
        grid = self.engine.grid.copy()
        rows, cols = grid.shape
        green_cells = np.where(grid == 0)
        if len(green_cells[0]) == 0:
            print("No hay celdas verdes para quemar.")
            return
        num_to_burn = max(1, int(len(green_cells[0]) * 0.01))
        indices = np.random.choice(len(green_cells[0]), num_to_burn, replace=False)
        for idx in indices:
            r, c = green_cells[0][idx], green_cells[1][idx]
            grid[r, c] = 2
        self.engine.reset(grid)
        self.current_month = 0
        self.time_slider.setValue(0)
        self.slider_label.setText("Mes 0")
        self.update_map()
        print(f"🔥 {num_to_burn} celdas quemadas aleatoriamente.")