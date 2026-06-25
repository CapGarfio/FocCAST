#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construye un grid real de usos del suelo a partir de CORINE 2018 (API REST)
usando la capa raster (export) para la provincia de Valencia.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import numpy as np
from PIL import Image
from io import BytesIO
from src.config import DATA_PROCESSED
from src.utils.logger import setup_logger

logger = setup_logger("BuildRealGrid")

# ------------------------------------------------------------
# Funcion de mapeo por distancia de color (con tolerancia)
# ------------------------------------------------------------
def closest_state(pixel_rgb):
    """
    Devuelve el estado mas cercano basado en distancia Euclidea en RGB.
    Los valores de pixel_rgb deben ser enteros entre 0 y 255.
    """
    # Lista de colores de referencia (R,G,B) y su estado asociado
    ref_colors = [
        # Urbano -> Poblacional (3)
        ((230, 0, 0), 3),      # rojo intenso
        ((230, 77, 77), 3),    # rojo claro
        ((204, 204, 204), 3),  # gris
        # Agricola -> Recuperacion (1)
        ((255, 255, 168), 1),  # amarillo palido
        ((255, 211, 128), 1),  # amarillo oscuro
        ((255, 170, 0), 1),    # naranja
        ((230, 230, 0), 1),    # amarillo limon
        # Bosques -> Verde (0)
        ((128, 255, 0), 0),    # verde claro
        ((0, 166, 0), 0),      # verde oscuro
        ((77, 255, 77), 0),    # verde brillante
        ((166, 255, 128), 0),  # verde amarillento
        ((166, 230, 77), 0),   # verde oliva
        ((204, 204, 0), 0),    # verde grisaceo
        # Agua y humedales -> Poblacional (3)
        ((166, 230, 230), 3),  # cian claro
        ((0, 204, 242), 3),    # azul claro
        ((0, 0, 230), 3),      # azul oscuro
    ]
    # Convertir pixel a enteros (por si vienen como uint8)
    pr, pg, pb = int(pixel_rgb[0]), int(pixel_rgb[1]), int(pixel_rgb[2])
    best_state = 0
    min_dist = float('inf')
    for (r, g, b), state in ref_colors:
        dr = pr - r
        dg = pg - g
        db = pb - b
        dist = (dr*dr + dg*dg + db*db) ** 0.5
        if dist < min_dist:
            min_dist = dist
            best_state = state
    # Si la distancia es muy grande, lo dejamos como Verde (0)
    if min_dist > 60:
        return 0
    return best_state

# ------------------------------------------------------------
# Funcion principal
# ------------------------------------------------------------
def build_valencia_grid():
    # Area de interes (Valencia aproximada)
    xmin, ymin, xmax, ymax = -1.5, 38.5, 0.5, 40.5
    bbox = f"{xmin},{ymin},{xmax},{ymax}"
    logger.info(f"Area: {bbox}")

    # 1. Descargar el raster de CORINE como PNG (capa 1)
    url = (
        "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/export"
        f"?bbox={bbox}"
        "&bboxSR=4326"
        "&size=800,800"          # Puedes aumentar a 1200,1200 para mas detalle
        "&format=png"
        "&transparent=true"
        "&f=image"
    )
    logger.info("Descargando raster CORINE...")
    resp = requests.get(url)
    if resp.status_code != 200:
        logger.error(f"Error descargando raster: {resp.status_code}")
        return

    # 2. Cargar imagen y convertir a array
    img = Image.open(BytesIO(resp.content))
    img = img.convert("RGB")
    raster = np.array(img)
    logger.info(f"Raster descargado: {raster.shape}")

    # 3. Redimensionar a nuestra malla (401x401)
    target_size = (401, 401)   # (ancho, alto)
    img_resized = img.resize(target_size, Image.NEAREST)
    grid = np.array(img_resized)   # (alto, ancho, 3)

    # 4. Mapear colores a estados
    state_grid = np.full((target_size[1], target_size[0]), 0, dtype=np.int8)
    for i in range(target_size[1]):      # filas (latitud)
        for j in range(target_size[0]):  # columnas (longitud)
            pixel = grid[i, j, :3]
            state_grid[i, j] = closest_state(pixel)

    # 5. Estadisticas
    unique, counts = np.unique(state_grid, return_counts=True)
    total = state_grid.size
    for st, cnt in zip(unique, counts):
        pct = cnt / total * 100
        name = {0: "Verde", 1: "Recuperacion", 2: "Quemado", 3: "Poblacional"}.get(st, "Desconocido")
        logger.info(f"Estado {st} ({name}): {cnt} celdas ({pct:.1f}%)")

    # 6. Guardar
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    out_path = os.path.join(DATA_PROCESSED, "valencia_grid.npy")
    np.save(out_path, state_grid)
    logger.info(f"Grid guardado en: {out_path}")

if __name__ == "__main__":
    build_valencia_grid()