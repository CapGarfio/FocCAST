# -*- coding: utf-8 -*-
"""
Widget que incrusta OpenStreetMap vía WebEngine y permite superponer capas raster.
"""
import os
import json
import base64
from io import BytesIO
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PIL import Image
import numpy as np

from src.config import GUI_RESOURCES, STATE_COLORS

class MapWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_loaded = False
        self.pending_grid_path = None

        html_path = os.path.join(GUI_RESOURCES, "map_template.html")
        self.load(QUrl.fromLocalFile(html_path))
        self.loadFinished.connect(self._on_load_finished)

    def _on_load_finished(self, ok):
        if ok:
            self.page_loaded = True
            print("🌍 Página HTML cargada.")
            QTimer.singleShot(1500, self._try_load_pending)
        else:
            print("❌ Error al cargar el HTML.")

    def _try_load_pending(self):
        if self.pending_grid_path:
            self.load_grid(self.pending_grid_path)
            self.pending_grid_path = None

    # ------------------------------------------------------------
    # Carga de grid desde archivo .npy
    # ------------------------------------------------------------
    def load_grid(self, grid_path: str):
        if not os.path.exists(grid_path):
            print(f"⚠️ Archivo no encontrado: {grid_path}")
            return
        if self.page_loaded:
            data = np.load(grid_path)
            self.update_grid(data)
        else:
            self.pending_grid_path = grid_path
            print("⏳ Mapa cargando, overlay pendiente...")

    # ------------------------------------------------------------
    # Actualización directa con array numpy
    # ------------------------------------------------------------
    def update_grid(self, grid_array: np.ndarray):
        """
        Convierte un array de estados a imagen y la superpone en el mapa.
        """
        if not self.page_loaded:
            print("⏳ Mapa no listo, guardando para más tarde...")
            # Podríamos almacenarlo, pero mejor esperar
            return
        try:
            b64_str = self._array_to_base64(grid_array)
            self._inject_overlay(b64_str)
            print("✅ Grid actualizado en el mapa.")
        except Exception as e:
            print(f"❌ Error al actualizar grid: {e}")

    # ------------------------------------------------------------
    # Conversión de array a base64 (PNG)
    # ------------------------------------------------------------
    def _array_to_base64(self, grid_array: np.ndarray) -> str:
        """Convierte un array 2D de estados a una imagen PNG en base64."""
        height, width = grid_array.shape
        img = Image.new('RGB', (width, height))
        pixels = img.load()
        for y in range(height):
            for x in range(width):
                state = grid_array[y, x]
                color = STATE_COLORS.get(state, (0, 0, 0))
                pixels[x, y] = color

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return b64_str

    # ------------------------------------------------------------
    # Inyección del overlay en el mapa (JavaScript)
    # ------------------------------------------------------------
    def _inject_overlay(self, b64_str: str, bounds=None):
        """Inyecta una imagen en base64 como overlay en el mapa Leaflet."""
        if bounds is None:
            # Coordenadas por defecto: provincia de Valencia
            bounds = [[38.5, -1.5], [40.5, 0.5]]

        js_code = f"""
        (function() {{
            var checkInterval = setInterval(function() {{
                if (typeof L !== 'undefined' && window.map) {{
                    clearInterval(checkInterval);
                    if (window._foccastOverlay) {{
                        window.map.removeLayer(window._foccastOverlay);
                    }}
                    var imageUrl = 'data:image/png;base64,{b64_str}';
                    var imageBounds = {bounds};
                    var overlay = L.imageOverlay(imageUrl, imageBounds);
                    overlay.addTo(window.map);
                    window._foccastOverlay = overlay;
                    // No ajustamos el zoom automáticamente para no perder el contorno
                    console.log('✅ Overlay actualizado.');
                }}
            }}, 300);
            setTimeout(function() {{ clearInterval(checkInterval); }}, 10000);
        }})();
        """
        self.page().runJavaScript(js_code)

    # ------------------------------------------------------------
    # Añadir contorno (GeoJSON)
    # ------------------------------------------------------------
    def add_contour(self, geo_json: dict, color: str = '#FF0000', weight: int = 3):
        """
        Añade un contorno (polígono) al mapa a partir de un GeoJSON.
        """
        js_code = f"""
        (function() {{
            var checkInterval = setInterval(function() {{
                if (typeof L !== 'undefined' && window.map) {{
                    clearInterval(checkInterval);
                    if (window._foccastContour) {{
                        window.map.removeLayer(window._foccastContour);
                    }}
                    var geojsonData = {json.dumps(geo_json)};
                    var contourLayer = L.geoJSON(geojsonData, {{
                        style: {{
                            color: '{color}',
                            weight: {weight},
                            opacity: 0.8,
                            fillOpacity: 0
                        }}
                    }}).addTo(window.map);
                    window._foccastContour = contourLayer;
                    window.map.fitBounds(contourLayer.getBounds());
                    console.log('✅ Contorno añadido.');
                }}
            }}, 300);
            setTimeout(function() {{ clearInterval(checkInterval); }}, 10000);
        }})();
        """
        self.page().runJavaScript(js_code)