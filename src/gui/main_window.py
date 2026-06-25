# -*- coding: utf-8 -*-
"""
Ventana principal de la aplicacion FocCAST.
Integra el mapa, el motor de simulacion y el control temporal.
"""
import os
import numpy as np
import requests
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QSlider, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer

from src.config import DATA_PROCESSED, DATA_RAW
from src.gui.map_widget import MapWidget
from src.core.engine import FocCASTEngine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FocCAST - Prediccion de Incendios Forestales")
        self.setGeometry(50, 50, 1400, 800)

        # --- Estado interno ---
        self.engine = None
        self.current_month = 0
        self.max_months = 60  # 5 años por defecto

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

        # Botones de control rapido
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

        # --- Inicializar carga de datos ---
        self.load_test_grid()

        # Timer para animacion
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animation_step)
        self.animation_running = False

    # ------------------------------------------------------------
    # Metodos de carga de datos
    # ------------------------------------------------------------
    def load_test_grid(self):
        """Carga el grid real de Valencia o, si no existe, el de prueba."""
        grid_path = os.path.join(DATA_PROCESSED, "valencia_grid.npy")
        if os.path.exists(grid_path):
            print(f"Cargando grid real de Valencia: {grid_path}")
            grid_data = np.load(grid_path)
            self.init_engine(grid_data)
            self.update_map()
            # Intentar cargar contorno (con manejo de errores)
            QTimer.singleShot(1500, self.load_province_contour)
        else:
            grid_path = os.path.join(DATA_PROCESSED, "test_grid.npy")
            if os.path.exists(grid_path):
                print(f"Cargando grid de prueba: {grid_path}")
                grid_data = np.load(grid_path)
                self.init_engine(grid_data)
                self.update_map()
            else:
                print("No se encontro ningun grid. Ejecuta primero scripts/build_real_grid.py o scripts/build_grid.py")

    def init_engine(self, grid_data):
        """Inicializa el motor de simulacion con el grid dado."""
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

    def load_province_contour(self):
        """Descarga el contorno de la provincia de Valencia (codigo INE 46) desde varias fuentes."""
        urls = [
            "https://www.ign.es/wfs-inspire/unidades-administrativas?request=GetFeature&typeName=au:AdministrativeUnit&outputFormat=json&srsName=EPSG:4326&cql_filter=code='46'"        
        ]
        for url in urls:
            try:
                print(f"Intentando contorno desde: {url}")
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'features' in data and len(data['features']) > 0:
                        self.map_widget.add_contour(data, color='#FF0000', weight=3)
                        print("Contorno de Valencia añadido correctamente.")
                        return
                    else:
                        print("La respuesta no contiene features.")
                else:
                    print(f"Error {response.status_code} en {url}")
            except Exception as e:
                print(f"Excepcion en {url}: {e}")
        
        # Intentar archivo local
        local_path = os.path.join(DATA_RAW, "valencia_province.geojson")
        if os.path.exists(local_path):
            try:
                import json
                with open(local_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'features' in data:
                    self.map_widget.add_contour(data, color='#FF0000', weight=3)
                    print("Contorno cargado desde archivo local.")
                    return
            except Exception as e:
                print(f"Error al cargar archivo local: {e}")
        
        print("No se pudo cargar el contorno de Valencia. La simulacion continuara sin el.")

    # ------------------------------------------------------------
    # Metodos de actualizacion del mapa y estadisticas
    # ------------------------------------------------------------
    def update_map(self):
        """Actualiza el mapa con el grid actual del engine."""
        if self.engine is None:
            return
        grid = self.engine.grid
        self.map_widget.update_grid(grid)
        self.update_stats(grid)

    def update_stats(self, grid):
        """Actualiza las estadisticas de estados en el panel derecho."""
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
        """Se ejecuta al mover el slider temporal."""
        self.current_month = value
        self.slider_label.setText(f"Mes {value}")
        if self.engine is not None:
            grid = self.engine.get_grid_at_time(value)
            self.map_widget.update_grid(grid)
            self.update_stats(grid)

    def reset_simulation(self):
        """Reinicia la simulacion al mes 0 y recarga el grid inicial."""
        if self.engine is not None and len(self.engine.history) > 0:
            initial_grid = self.engine.history[0]
            self.engine.reset(initial_grid)
            self.current_month = 0
            self.time_slider.setValue(0)
            self.slider_label.setText("Mes 0")
            self.update_map()
            print("Simulacion reiniciada.")

    # ------------------------------------------------------------
    # Metodos de animacion (reproduccion automatica)
    # ------------------------------------------------------------
    def toggle_animation(self):
        """Inicia o detiene la reproduccion automatica."""
        if self.animation_running:
            self.animation_timer.stop()
            self.btn_play.setText("▶")
            self.animation_running = False
        else:
            if self.current_month >= self.max_months:
                self.reset_simulation()
            self.animation_timer.start(300)  # 300ms por paso
            self.btn_play.setText("⏸")
            self.animation_running = True

    def animation_step(self):
        """Avanza un mes en la animacion."""
        if self.engine is None:
            self.toggle_animation()
            return

        next_month = self.current_month + 1
        if next_month > self.max_months:
            self.toggle_animation()
            return

        self.time_slider.setValue(next_month)
        # on_slider_change se dispara automaticamente

    # ------------------------------------------------------------
    # Metodo de prueba: ignicion aleatoria
    # ------------------------------------------------------------
    def random_ignition(self):
        """Quema aleatoriamente un 1% de las celdas verdes para probar la simulacion."""
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
            grid[r, c] = 2  # Quemado

        self.engine.reset(grid)
        self.current_month = 0
        self.time_slider.setValue(0)
        self.slider_label.setText("Mes 0")
        self.update_map()
        print(f"🔥 {num_to_burn} celdas quemadas aleatoriamente.")