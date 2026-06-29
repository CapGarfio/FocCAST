#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construye un grid real de usos del suelo a partir de CORINE 2018 (API REST)
para una provincia o comarca dada por su código INE y/o bounding box.
Uso: python scripts/build_real_grid.py [codigo_provincia] [--bbox xmin,ymin,xmax,ymax]
Ejemplo: python scripts/build_real_grid.py 46 --bbox -0.7,39.0,-0.3,39.4  (La Ribera Alta)
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
from src.data.spain.provincias import get_province_bbox

logger = setup_logger("BuildRealGrid")

# ------------------------------------------------------------
# Mapeo de colores por distancia Euclidea (con tolerancia)
# ------------------------------------------------------------
def closest_state(pixel_rgb):
    """
    Devuelve el estado mas cercano basado en distancia Euclidea en RGB.
    Los valores de pixel_rgb deben ser enteros entre 0 y 255.
    """
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
# Funcion principal de construccion de grid desde bbox
# ------------------------------------------------------------
def build_grid_from_bbox(province_code, bbox, target_size=(401, 401), name_suffix="", cell_size=500):
    """
    Genera grid a partir de un bbox dado.
    cell_size: se usa para calcular la resolución (por ahora no implementado).
    """
    if bbox is None:
        logger.error("bbox no proporcionado.")
        return False

    xmin, ymin, xmax, ymax = bbox
    bbox_str = f"{xmin},{ymin},{xmax},{ymax}"
    logger.info(f"Generando grid para bbox: {bbox_str}")

    # 1. Descargar raster de CORINE (capa 1)
    url = (
        "https://image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/export"
        f"?bbox={bbox_str}"
        "&bboxSR=4326"
        f"&size={target_size[0]},{target_size[1]}"
        "&format=png"
        "&transparent=true"
        "&f=image"
    )
    logger.info("Descargando raster CORINE...")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Error descargando raster: {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Excepcion en descarga: {e}")
        return False

    img = Image.open(BytesIO(resp.content))
    img = img.convert("RGB")
    raster = np.array(img)
    logger.info(f"Raster descargado: {raster.shape}")

    # 2. Redimensionar al tamaño objetivo
    img_resized = img.resize(target_size, Image.NEAREST)
    grid = np.array(img_resized)

    # 3. Mapear colores a estados
    state_grid = np.full((target_size[1], target_size[0]), 0, dtype=np.int8)
    for i in range(target_size[1]):
        for j in range(target_size[0]):
            pixel = grid[i, j, :3]
            state_grid[i, j] = closest_state(pixel)

    # 4. Estadisticas
    unique, counts = np.unique(state_grid, return_counts=True)
    total = state_grid.size
    for st, cnt in zip(unique, counts):
        pct = cnt / total * 100
        name = {0: "Verde", 1: "Recuperacion", 2: "Quemado", 3: "Poblacional"}.get(st, "Desconocido")
        logger.info(f"Estado {st} ({name}): {cnt} celdas ({pct:.1f}%)")

    # 5. Guardar
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    out_path = os.path.join(DATA_PROCESSED, f"grid_{province_code}{name_suffix}.npy")
    np.save(out_path, state_grid)
    logger.info(f"Grid guardado en: {out_path}")
    return True

# ------------------------------------------------------------
# Funcion para construir grid de provincia (por compatibilidad)
# ------------------------------------------------------------
def build_province_grid(province_code, target_size=(401, 401)):
    """Construye grid para una provincia usando su bbox."""
    bbox = get_province_bbox(province_code)
    if bbox is None:
        logger.error(f"Codigo de provincia {province_code} no encontrado.")
        return False
    return build_grid_from_bbox(province_code, bbox, target_size, "")

# ------------------------------------------------------------
# Punto de entrada para uso directo desde terminal
# ------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Genera grid de CORINE para una provincia o comarca.")
    parser.add_argument("province", nargs="?", default="46", help="Codigo INE de la provincia (ej: 28 para Madrid)")
    parser.add_argument("--bbox", help="Bounding box personalizado: xmin,ymin,xmax,ymax")
    parser.add_argument("--suffix", default="", help="Sufijo para el nombre del archivo")
    args = parser.parse_args()

    if args.bbox:
        bbox = [float(x) for x in args.bbox.split(",")]
        build_grid_from_bbox(args.province, bbox, name_suffix=args.suffix)
    else:
        build_province_grid(args.province)