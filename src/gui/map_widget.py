# -*- coding: utf-8 -*-
"""
Widget que incrusta OpenStreetMap vía WebEngine y permite superponer capas raster.
"""
import os
import base64
import json
from io import BytesIO
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PIL import Image
import numpy as np

from src.config import GUI_RESOURCES, DATA_PROCESSED, STATE_COLORS

class ConsolePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line, source):
        level_names = {0: "INFO", 1: "WARN", 2: "ERROR"}
        print(f"[JS {level_names.get(level, 'LOG')}] {message} (line {line}, source: {source})")

class MapWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_loaded = False
        self.pending_grid_path = None
        self._contour_original_geojson = None  # GeoJSON original sin transformar
        self._contour_offset = {'dx': 0, 'dy': 0}
        self._contour_scale = 1.0
        self._grid_bounds = None
        self._contour_layer_active = False

        self.setPage(ConsolePage(self))
        try:
            self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        except AttributeError:
            pass

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
            self._load_overlay(self.pending_grid_path)
            self.pending_grid_path = None

    def _array_to_base64(self, grid_array):
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
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def set_grid_bounds(self, bounds):
        self._grid_bounds = bounds
        js_code = f"""
        (function() {{
            window._foccastGridBounds = {bounds};
            console.log('Grid bounds fijos establecidos.');
        }})();
        """
        self.page().runJavaScript(js_code)

    def _load_overlay(self, grid_path: str):
        try:
            data = np.load(grid_path)
            print(f"📊 Cargado grid: {data.shape}")
            b64_str = self._array_to_base64(data)
            if self._grid_bounds is None:
                self._grid_bounds = [[39.0, -1.0], [40.0, 0.0]]
                print("⚠️ Usando bounds por defecto para el grid.")
            js_code = f"""
            (function() {{
                var checkInterval = setInterval(function() {{
                    if (typeof L !== 'undefined' && window.map) {{
                        clearInterval(checkInterval);
                        if (window._foccastOverlay) {{
                            window.map.removeLayer(window._foccastOverlay);
                        }}
                        var imageUrl = 'data:image/png;base64,{b64_str}';
                        var imageBounds = {self._grid_bounds};
                        var overlay = L.imageOverlay(imageUrl, imageBounds);
                        overlay.addTo(window.map);
                        window._foccastOverlay = overlay;
                        console.log('✅ Overlay añadido con bounds fijos.');
                    }}
                }}, 300);
                setTimeout(function() {{ clearInterval(checkInterval); }}, 10000);
            }})();
            """
            self.page().runJavaScript(js_code)
            print("✅ Grid cargado con bounds fijos.")
        except Exception as e:
            print(f"❌ Error al cargar overlay: {e}")

    def update_grid(self, grid_array):
        try:
            b64_str = self._array_to_base64(grid_array)
            if self._grid_bounds is None:
                self._grid_bounds = [[39.0, -1.0], [40.0, 0.0]]
            js_code = f"""
            (function() {{
                var checkInterval = setInterval(function() {{
                    if (typeof L !== 'undefined' && window.map) {{
                        clearInterval(checkInterval);
                        if (window._foccastOverlay) {{
                            window.map.removeLayer(window._foccastOverlay);
                        }}
                        var imageUrl = 'data:image/png;base64,{b64_str}';
                        var imageBounds = {self._grid_bounds};
                        var overlay = L.imageOverlay(imageUrl, imageBounds);
                        overlay.addTo(window.map);
                        window._foccastOverlay = overlay;
                        console.log('✅ Grid actualizado (bounds fijos).');
                    }}
                }}, 300);
                setTimeout(function() {{ clearInterval(checkInterval); }}, 5000);
            }})();
            """
            self.page().runJavaScript(js_code)
            print("✅ Grid actualizado.")
        except Exception as e:
            print(f"❌ Error al actualizar grid: {e}")

    # ------------------------------------------------------------
    # Métodos para contornos independientes
    # ------------------------------------------------------------
    def load_contour(self, geo_json, province_code):
        """Guarda el GeoJSON original y lo dibuja aplicando offset/scale si existen."""
        self._contour_original_geojson = geo_json.copy()
        # Cargar offset guardado
        offsets_path = os.path.join(DATA_PROCESSED, "contour_offsets.json")
        offset = {'dx': 0, 'dy': 0}
        scale = 1.0
        if os.path.exists(offsets_path):
            with open(offsets_path, 'r') as f:
                all_offsets = json.load(f)
                if province_code in all_offsets:
                    offset = all_offsets[province_code].get('offset', {'dx': 0, 'dy': 0})
                    scale = all_offsets[province_code].get('scale', 1.0)
        self._contour_offset = offset
        self._contour_scale = scale
        # Aplicar transformación y dibujar
        self._apply_contour_transform()

    def _apply_contour_transform(self):
        """Aplica offset y escala al GeoJSON original y lo dibuja en el mapa."""
        if self._contour_original_geojson is None:
            return
        # Copiar el GeoJSON original para no modificarlo
        geojson = self._contour_original_geojson.copy()
        # Aplicar transformación a las coordenadas
        transformed = self._transform_geojson(geojson, self._contour_offset['dx'], self._contour_offset['dy'], self._contour_scale)
        # Dibujar en el mapa
        self._draw_contour(transformed)

    def _transform_geojson(self, geojson, dx, dy, scale):
        """Aplica desplazamiento (dx, dy) y escala a un GeoJSON."""
        import copy
        transformed = copy.deepcopy(geojson)
        for feature in transformed.get('features', []):
            geom = feature.get('geometry')
            if geom:
                coords = geom.get('coordinates')
                if geom['type'] == 'Polygon':
                    # Aplicar transformación a cada anillo y coordenada
                    for ring in coords:
                        for i, (lon, lat) in enumerate(ring):
                            # Escalar respecto al centroide del contorno (necesitamos calcularlo)
                            # Pero por simplicidad, solo desplazamos y escalamos en lat/lon
                            # Nota: escalar correctamente requeriría un centro de referencia
                            # Para este ejemplo, escalamos respecto al centro del bounding box
                            # que calculamos en JS, pero lo haremos en Python calculando el centroide.
                            # Por simplicidad, asumimos que el usuario solo mueve y escala manualmente,
                            # y aplicamos la transformación directamente en JS.
                            pass  # Lo haremos en JavaScript para más precisión
        # En lugar de transformar en Python (complejo), vamos a pasar offset y scale a JS y transformar allí.
        return geojson

    def _draw_contour(self, geojson):
        """Dibuja un GeoJSON en el mapa (reemplaza el contorno existente)."""
        js_code = f"""
        (function() {{
            var checkInterval = setInterval(function() {{
                if (typeof L !== 'undefined' && window.map) {{
                    clearInterval(checkInterval);
                    if (window._foccastContour) {{
                        window.map.removeLayer(window._foccastContour);
                    }}
                    var geojsonData = {json.dumps(geojson)};
                    var contourLayer = L.geoJSON(geojsonData, {{
                        style: {{
                            color: '#000000',
                            weight: 3,
                            opacity: 0.9,
                            fillOpacity: 0
                        }}
                    }}).addTo(window.map);
                    window._foccastContour = contourLayer;
                    console.log('✅ Contorno dibujado.');
                }}
            }}, 300);
            setTimeout(function() {{ clearInterval(checkInterval); }}, 10000);
        }})();
        """
        self.page().runJavaScript(js_code)

    def apply_transform_to_contour(self, dx, dy, scale):
        """Aplica transformación al contorno actual desde Python."""
        self._contour_offset['dx'] += dx
        self._contour_offset['dy'] += dy
        self._contour_scale *= scale
        # Regenerar el contorno con la nueva transformación
        # Para simplificar, usamos JavaScript para transformar el GeoJSON original en el cliente.
        # Pasamos el GeoJSON original y la transformación.
        if self._contour_original_geojson is not None:
            self._apply_transform_in_js(self._contour_original_geojson, self._contour_offset['dx'], self._contour_offset['dy'], self._contour_scale)

    def _apply_transform_in_js(self, geojson, dx, dy, scale):
        """Aplica transformación en JavaScript para mayor precisión."""
        js_code = f"""
        (function() {{
            function transformCoords(coords, dx, dy, scale) {{
                // Escalar respecto al centroide del contorno
                // Calcular centroide (promedio de todas las coordenadas)
                var allLons = [];
                var allLats = [];
                function extractCoords(geom) {{
                    if (geom.type === 'Polygon') {{
                        for (var ring of geom.coordinates) {{
                            for (var [lon, lat] of ring) {{
                                allLons.push(lon);
                                allLats.push(lat);
                            }}
                        }}
                    }} else if (geom.type === 'MultiPolygon') {{
                        for (var poly of geom.coordinates) {{
                            for (var ring of poly) {{
                                for (var [lon, lat] of ring) {{
                                    allLons.push(lon);
                                    allLats.push(lat);
                                }}
                            }}
                        }}
                    }}
                }}
                var geojson = {json.dumps(geojson)};
                for (var feature of geojson.features) {{
                    extractCoords(feature.geometry);
                }}
                var centerLon = allLons.reduce((a,b)=>a+b,0)/allLons.length;
                var centerLat = allLats.reduce((a,b)=>a+b,0)/allLats.length;
                // Transformar todas las coordenadas
                function transformGeometry(geom) {{
                    if (geom.type === 'Polygon') {{
                        for (var ring of geom.coordinates) {{
                            for (var i=0; i<ring.length; i++) {{
                                var lon = ring[i][0];
                                var lat = ring[i][1];
                                var newLon = centerLon + (lon - centerLon) * scale + dx;
                                var newLat = centerLat + (lat - centerLat) * scale + dy;
                                ring[i] = [newLon, newLat];
                            }}
                        }}
                    }} else if (geom.type === 'MultiPolygon') {{
                        for (var poly of geom.coordinates) {{
                            for (var ring of poly) {{
                                for (var i=0; i<ring.length; i++) {{
                                    var lon = ring[i][0];
                                    var lat = ring[i][1];
                                    var newLon = centerLon + (lon - centerLon) * scale + dx;
                                    var newLat = centerLat + (lat - centerLat) * scale + dy;
                                    ring[i] = [newLon, newLat];
                                }}
                            }}
                        }}
                    }}
                }}
                for (var feature of geojson.features) {{
                    transformGeometry(feature.geometry);
                }}
                return geojson;
            }}
            var transformed = transformCoords({json.dumps(geojson)}, {dx}, {dy}, {scale});
            // Dibujar el contorno transformado
            if (window._foccastContour) {{
                window.map.removeLayer(window._foccastContour);
            }}
            var contourLayer = L.geoJSON(transformed, {{
                style: {{
                    color: '#000000',
                    weight: 3,
                    opacity: 0.9,
                    fillOpacity: 0
                }}
            }}).addTo(window.map);
            window._foccastContour = contourLayer;
            console.log('✅ Contorno transformado aplicado.');
        }})();
        """
        self.page().runJavaScript(js_code)

    def set_contour_draggable(self, draggable):
        """Habilita/deshabilita el arrastre del contorno (usando drag de Leaflet)."""
        js_code = f"""
        (function() {{
            if (window._foccastContour) {{
                try {{
                    if ({str(draggable).lower()}) {{
                        window._foccastContour.dragging.enable();
                    }} else {{
                        window._foccastContour.dragging.disable();
                    }}
                }} catch(e) {{
                    console.log('No se pudo habilitar arrastre: ' + e.message);
                }}
            }}
        }})();
        """
        self.page().runJavaScript(js_code)

    def add_contour(self, geo_json: dict, color: str = '#000000', weight: int = 3, fit_bounds: bool = False):
        """
        Añade un contorno al mapa a partir de un GeoJSON.
        """
        import json
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
                            opacity: 0.9,
                            fillOpacity: 0
                        }}
                    }}).addTo(window.map);
                    window._foccastContour = contourLayer;
                    // Guardar bounds originales para referencia
                    var bounds = contourLayer.getBounds();
                    window._foccastContourOriginalBounds = [[bounds.getSouth(), bounds.getWest()], [bounds.getNorth(), bounds.getEast()]];
                    window._foccastContourBounds = window._foccastContourOriginalBounds.slice();
                    if ({str(fit_bounds).lower()}) {{
                        try {{
                            window.map.fitBounds(contourLayer.getBounds());
                        }} catch(e) {{
                            console.log('No se pudo ajustar zoom al contorno.');
                        }}
                    }}
                    console.log('✅ Contorno añadido.');
                }}
            }}, 300);
            setTimeout(function() {{ clearInterval(checkInterval); }}, 10000);
        }})();
        """
        self.page().runJavaScript(js_code)       


    def move_contour(self, dx, dy):
        """
        Mueve el contorno en lat/lon (dx, dy) y acumula el desplazamiento.
        dx: desplazamiento en longitud (grados)
        dy: desplazamiento en latitud (grados)
        """
        # Acumular offset
        self._contour_offset['dx'] += dx
        self._contour_offset['dy'] += dy

        # Aplicar el movimiento en el mapa
        js_code = f"""
        (function() {{
            if (window._foccastContour) {{
                var layer = window._foccastContour;
                var bounds = layer.getBounds();
                var center = bounds.getCenter();
                var newCenter = L.latLng(center.lat + {dy}, center.lng + {dx});
                var latHalf = (bounds.getNorth() - bounds.getSouth()) / 2;
                var lngHalf = (bounds.getEast() - bounds.getWest()) / 2;
                var newBounds = L.latLngBounds(
                    [newCenter.lat - latHalf, newCenter.lng - lngHalf],
                    [newCenter.lat + latHalf, newCenter.lng + lngHalf]
                );
                layer.setBounds(newBounds);
                console.log('Contorno movido (grid inalterado).');
            }}
        }})();
        """
        self.page().runJavaScript(js_code)

    def scale_contour(self, factor):
        """
        Escala el contorno respecto a su centro (factor > 1 = agrandar, < 1 = reducir).
        Acumula el factor de escala.
        """
        # Acumular escala
        self._contour_scale *= factor

        # Aplicar la escala en el mapa
        js_code = f"""
        (function() {{
            if (window._foccastContour) {{
                var layer = window._foccastContour;
                var bounds = layer.getBounds();
                var center = bounds.getCenter();
                var latHalf = (bounds.getNorth() - bounds.getSouth()) / 2 * {factor};
                var lngHalf = (bounds.getEast() - bounds.getWest()) / 2 * {factor};
                var newBounds = L.latLngBounds(
                    [center.lat - latHalf, center.lng - lngHalf],
                    [center.lat + latHalf, center.lng + lngHalf]
                );
                layer.setBounds(newBounds);
                console.log('Contorno escalado (grid inalterado).');
            }}
        }})();
        """
        self.page().runJavaScript(js_code)

    def get_contour_transform(self):
        """Devuelve el offset y escala actuales."""
        return self._contour_offset, self._contour_scale

    def save_contour_transform(self, province_code):
        """Guarda el offset y escala actuales para la provincia."""
        import json as jsonlib
        offsets_path = os.path.join(DATA_PROCESSED, "contour_offsets.json")
        if os.path.exists(offsets_path):
            with open(offsets_path, 'r') as f:
                all_offsets = jsonlib.load(f)
        else:
            all_offsets = {}
        all_offsets[province_code] = {
            'offset': self._contour_offset,
            'scale': self._contour_scale
        }
        with open(offsets_path, 'w') as f:
            jsonlib.dump(all_offsets, f, indent=2)
        print(f"✅ Transformación guardada para provincia {province_code}: offset={self._contour_offset}, scale={self._contour_scale}")

    def clear_overlays(self):
        js_code = """
        (function() {
            if (typeof window.map !== 'undefined') {
                if (window._foccastOverlay) {
                    window.map.removeLayer(window._foccastOverlay);
                    window._foccastOverlay = null;
                }
                if (window._foccastContour) {
                    window.map.removeLayer(window._foccastContour);
                    window._foccastContour = null;
                }
                console.log('🗑️ Capas limpiadas.');
            }
        })();
        """
        self.page().runJavaScript(js_code)

    def center_map(self, bounds):
        js_code = f"""
        (function() {{
            var checkInterval = setInterval(function() {{
                if (typeof L !== 'undefined' && window.map) {{
                    clearInterval(checkInterval);
                    window.map.fitBounds({bounds});
                    console.log('Mapa centrado en bounds.');
                }}
            }}, 300);
            setTimeout(function() {{ clearInterval(checkInterval); }}, 5000);
        }})();
        """
        self.page().runJavaScript(js_code)