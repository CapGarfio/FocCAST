# -*- coding: utf-8 -*-
"""
Ventana principal de la aplicacion FocCAST.
"""
import os
import sys
import json
import numpy as np
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSlider, QPushButton, QFrame, QComboBox, QLineEdit
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

    def __init__(self, province_code, bbox, suffix="", cell_size=500):
        super().__init__()
        self.province_code = province_code
        self.bbox = bbox
        self.suffix = suffix
        self.cell_size = cell_size

    def run(self):
        try:
            from scripts.build_real_grid import build_grid_from_bbox
            success = build_grid_from_bbox(
                self.province_code,
                self.bbox,
                name_suffix=self.suffix,
                cell_size=self.cell_size
            )
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
        self.setWindowTitle("FocCAST - Predicción de Incendios Forestales")
        self.setGeometry(50, 50, 1400, 800)

        # --- Estado interno ---
        self.engine = None
        self.current_month = 0
        self.max_months = 60
        self.worker = None
        self.cell_size = 500
        self.adjust_mode = False

        # --- Widget central ---
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
        right_panel.setFixedWidth(320)
        right_panel.setStyleSheet("background-color: #2c3e50; border-radius: 5px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_layout.setSpacing(10)

        # Título
        title_label = QLabel("📊 Panel de Control")
        title_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold; padding: 10px;")
        right_layout.addWidget(title_label)

        # --- Selector de provincia ---
        right_layout.addWidget(QLabel("Seleccionar provincia:"))
        self.province_combo = QComboBox()
        self.province_combo.setStyleSheet("background-color: white; padding: 5px; border-radius: 3px;")
        for code, name in get_province_list():
            self.province_combo.addItem(f"{code} - {name}", code)
        index = self.province_combo.findData("46")
        if index >= 0:
            self.province_combo.setCurrentIndex(index)
        self.province_combo.currentIndexChanged.connect(self.on_province_changed)
        right_layout.addWidget(self.province_combo)

        # --- Selector de comarca ---
        right_layout.addWidget(QLabel("Comarca (opcional):"))
        self.comarca_combo = QComboBox()
        self.comarca_combo.setStyleSheet("background-color: white; padding: 5px; border-radius: 3px;")
        self.comarca_combo.addItem("Toda la provincia", None)
        right_layout.addWidget(self.comarca_combo)

        # --- Tamaño de celda ---
        right_layout.addWidget(QLabel("Tamaño de celda (metros):"))
        self.cell_size_input = QLineEdit("500")
        self.cell_size_input.setStyleSheet("background-color: white; padding: 5px; border-radius: 3px;")
        right_layout.addWidget(self.cell_size_input)

        # --- Botones principales ---
        self.load_btn = QPushButton("📥 Cargar provincia")
        self.load_btn.setStyleSheet("background-color: #2980b9; color: white; padding: 8px; border-radius: 5px;")
        self.load_btn.clicked.connect(self.load_selected_province)
        right_layout.addWidget(self.load_btn)

        apply_cell_btn = QPushButton("📏 Aplicar tamaño")
        apply_cell_btn.setStyleSheet("background-color: #8e44ad; color: white; padding: 8px; border-radius: 5px;")
        apply_cell_btn.clicked.connect(self.apply_cell_size)
        right_layout.addWidget(apply_cell_btn)

        center_btn = QPushButton("📍 Centrar en provincia")
        center_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px; border-radius: 5px;")
        center_btn.clicked.connect(self.center_on_province)
        right_layout.addWidget(center_btn)

        # --- Modo ajuste de contorno ---
        self.adjust_btn = QPushButton("🎯 Ajustar contorno")
        self.adjust_btn.setStyleSheet("background-color: #f39c12; color: white; padding: 8px; border-radius: 5px;")
        self.adjust_btn.clicked.connect(self.toggle_adjust_mode)
        right_layout.addWidget(self.adjust_btn)

        self.save_offset_btn = QPushButton("💾 Guardar posición")
        self.save_offset_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 8px; border-radius: 5px;")
        self.save_offset_btn.clicked.connect(self.save_contour_offset)
        self.save_offset_btn.setVisible(False)
        right_layout.addWidget(self.save_offset_btn)

        # Botones de desplazamiento
        self.move_buttons_frame = QWidget()
        move_layout = QHBoxLayout(self.move_buttons_frame)
        move_layout.setContentsMargins(0, 0, 0, 0)
        for label, dx, dy in [("←", -0.001, 0), ("→", 0.001, 0), ("↑", 0, 0.001), ("↓", 0, -0.001)]:
            btn = QPushButton(label)
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda checked, dx=dx, dy=dy: self.move_contour(dx, dy))
            move_layout.addWidget(btn)
        self.move_buttons_frame.setVisible(False)
        right_layout.addWidget(self.move_buttons_frame)

        # Botones de escala
        self.scale_buttons_frame = QWidget()
        scale_layout = QHBoxLayout(self.scale_buttons_frame)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        for label, factor in [("🔍+", 1.1), ("🔍-", 0.9)]:
            btn = QPushButton(label)
            btn.setFixedSize(40, 40)
            btn.clicked.connect(lambda checked, factor=factor: self.scale_contour(factor))
            scale_layout.addWidget(btn)
        self.scale_buttons_frame.setVisible(False)
        right_layout.addWidget(self.scale_buttons_frame)

        # --- Información del grid ---
        self.info_label = QLabel("Estado: Cargando...\nCeldas: -")
        self.info_label.setStyleSheet("color: #ecf0f1; padding: 10px; background-color: #34495e; border-radius: 5px;")
        right_layout.addWidget(self.info_label)

        # --- Estadísticas ---
        self.stats_label = QLabel("Verde: 0%\nRecuperación: 0%\nQuemado: 0%\nPoblacional: 0%")
        self.stats_label.setStyleSheet("color: #ecf0f1; padding: 10px; background-color: #34495e; border-radius: 5px;")
        right_layout.addWidget(self.stats_label)

        # --- Botones de reinicio y pruebas ---
        reset_btn = QPushButton("🔄 Reiniciar simulación")
        reset_btn.setStyleSheet("background-color: #e67e22; color: white; padding: 8px; border-radius: 5px;")
        reset_btn.clicked.connect(self.reset_simulation)
        right_layout.addWidget(reset_btn)

        fire_btn = QPushButton("🔥 Ignición aleatoria")
        fire_btn.setStyleSheet("background-color: #c0392b; color: white; padding: 8px; border-radius: 5px;")
        fire_btn.clicked.connect(self.random_ignition)
        right_layout.addWidget(fire_btn)

        right_layout.addStretch()

        # --- Ensamblar layout ---
        main_layout.addWidget(left_column, stretch=4)
        main_layout.addWidget(right_panel, stretch=1)

        # --- Timer de animación ---
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animation_step)
        self.animation_running = False

        # --- Inicializar ---
        self.on_province_changed()
        self.load_test_grid()

    # ------------------------------------------------------------
    # Métodos de carga de datos
    # ------------------------------------------------------------
    def load_test_grid(self):
        index = self.province_combo.findData("46")
        if index >= 0:
            self.province_combo.setCurrentIndex(index)
        self.load_selected_province()

    def on_province_changed(self):
        province_code = self.province_combo.currentData()
        self.comarca_combo.clear()
        self.comarca_combo.addItem("Toda la provincia", None)
        comarcas = get_comarcas(province_code)
        for name, bbox in comarcas:
            self.comarca_combo.addItem(name, bbox)
        self.comarca_combo.setCurrentIndex(0)

    def load_selected_province(self):
        province_code = self.province_combo.currentData()
        if not province_code:
            return

        try:
            self.cell_size = int(self.cell_size_input.text())
            if self.cell_size < 100:
                self.cell_size = 100
                self.cell_size_input.setText("100")
            elif self.cell_size > 5000:
                self.cell_size = 5000
                self.cell_size_input.setText("5000")
        except ValueError:
            self.cell_size = 500
            self.cell_size_input.setText("500")

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

        # Limpiar capas anteriores
        self.map_widget.clear_overlays()

        # Establecer bounds fijos para el grid
        grid_bounds = [[bbox[1], bbox[0]], [bbox[3], bbox[2]]]
        self.map_widget.set_grid_bounds(grid_bounds)

        self.province_combo.setEnabled(False)
        self.comarca_combo.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.info_label.setText(f"Generando grid ({self.cell_size}m)...")

        self.worker = GridGenerationWorker(province_code, bbox, suffix, self.cell_size)
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
            QTimer.singleShot(500, lambda: self.load_province_contour(province_code))
            self.info_label.setText(f"Provincia cargada. Celda: {self.cell_size}m")
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
        self.info_label.setText(f"Simulación lista\nCeldas: {rows}x{cols} ({self.cell_size}m)")
        self.update_stats(grid_data)

    # ------------------------------------------------------------
    # Métodos de contorno
    # ------------------------------------------------------------
    def load_province_contour(self, province_code):
        import json
        geojson_path = os.path.join(DATA_PROCESSED, "provincias.geojson")
        if not os.path.exists(geojson_path):
            print(f"⚠️ No se encontró {geojson_path}")
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

        sample = features[0]
        props = sample.get('properties', {})
        print(f"📋 Campos en properties: {list(props.keys())}")

        found = None
        for feature in features:
            props = feature.get('properties', {})
            cod = props.get('cod_prov') or props.get('codigo') or props.get('ine') or props.get('id')
            if cod:
                if str(cod).zfill(2) == province_code:
                    found = feature
                    break

        if not found:
            idx = self.province_combo.findData(province_code)
            if idx >= 0:
                provincia_nombre = self.province_combo.itemText(idx).split(" - ")[1] if " - " in self.province_combo.itemText(idx) else None
                if provincia_nombre:
                    for feature in features:
                        name = feature.get('properties', {}).get('name', '')
                        if provincia_nombre.lower() in name.lower():
                            found = feature
                            break

        if found:
            province_geojson = {"type": "FeatureCollection", "features": [found]}
            self.map_widget.load_contour_with_offset(province_code, province_geojson)
            print(f"✅ Contorno de provincia {province_code} cargado.")
        else:
            print(f"❌ No se encontró la provincia {province_code}")

    # ------------------------------------------------------------
    # Métodos de ajuste de contorno
    # ------------------------------------------------------------
    def toggle_adjust_mode(self):
        self.adjust_mode = not self.adjust_mode
        if self.adjust_mode:
            self.adjust_btn.setText("🔒 Bloquear contorno")
            self.save_offset_btn.setVisible(True)
            self.move_buttons_frame.setVisible(True)
            self.scale_buttons_frame.setVisible(True)
            self.map_widget.set_contour_draggable(True)
        else:
            self.adjust_btn.setText("🎯 Ajustar contorno")
            self.save_offset_btn.setVisible(False)
            self.move_buttons_frame.setVisible(False)
            self.scale_buttons_frame.setVisible(False)
            self.map_widget.set_contour_draggable(False)

    def move_contour(self, dx, dy):
        self.map_widget.move_contour(dx, dy)
        # Actualizar offset en el widget (ya se actualiza internamente)

    def scale_contour(self, factor):
        self.map_widget.scale_contour(factor)
        # Actualizar escala en el widget (ya se actualiza internamente)

    def save_contour_offset(self):
        province_code = self.province_combo.currentData()
        if not province_code:
            return

        # Obtener offset y escala actuales
        offset = getattr(self.map_widget, '_contour_offset', {'dx': 0, 'dy': 0})
        scale = getattr(self.map_widget, '_contour_scale', 1.0)

        data_to_save = {'offset': offset, 'scale': scale}
        offsets_path = os.path.join(DATA_PROCESSED, "contour_offsets.json")
        if os.path.exists(offsets_path):
            with open(offsets_path, 'r', encoding='utf-8') as f:
                all_offsets = json.load(f)
        else:
            all_offsets = {}

        all_offsets[province_code] = data_to_save
        with open(offsets_path, 'w', encoding='utf-8') as f:
            json.dump(all_offsets, f, indent=2, ensure_ascii=False)

        print(f"✅ Offset y escala guardados para provincia {province_code}: offset={offset}, scale={scale}")
        self.info_label.setText(f"Posición guardada para provincia {province_code}")

        # Desactivar modo ajuste automáticamente
        if self.adjust_mode:
            self.toggle_adjust_mode()

    # ------------------------------------------------------------
    # Métodos de centrado y tamaño de celda
    # ------------------------------------------------------------
    def center_on_province(self):
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

    def apply_cell_size(self):
        try:
            size = int(self.cell_size_input.text())
            if size < 100:
                size = 100
                self.cell_size_input.setText("100")
            elif size > 5000:
                size = 5000
                self.cell_size_input.setText("5000")
            self.cell_size = size
            print(f"📏 Tamaño de celda cambiado a {size}m")
            self.load_selected_province()
        except ValueError:
            print("⚠️ Introduce un número válido.")
            self.cell_size_input.setText(str(self.cell_size))

    # ------------------------------------------------------------
    # Métodos de actualización del mapa y estadísticas
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
            name = {0: "Verde", 1: "Recuperación", 2: "Quemado", 3: "Poblacional"}.get(st, "Desconocido")
            stats[name] = pct
        text = (
            f"Verde: {stats.get('Verde', 0):.1f}%\n"
            f"Recuperación: {stats.get('Recuperación', 0):.1f}%\n"
            f"Quemado: {stats.get('Quemado', 0):.1f}%\n"
            f"Poblacional: {stats.get('Poblacional', 0):.1f}%"
        )
        self.stats_label.setText(text)

    # ------------------------------------------------------------
    # Métodos del slider y control temporal
    # ------------------------------------------------------------
    def on_slider_change(self, value):
        """Se ejecuta al mover el slider temporal."""
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
            print("Simulación reiniciada.")

    # ------------------------------------------------------------
    # Métodos de animación
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
    # Método de prueba: ignición aleatoria
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