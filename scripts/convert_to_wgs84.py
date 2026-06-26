#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte un GeoJSON de UTM (EPSG:25830 o EPSG:32630) a WGS84 (EPSG:4326).
"""
import os
import sys
import json
import geopandas as gpd
from shapely.geometry import shape

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import DATA_PROCESSED

def convert_geojson_to_wgs84(input_path, output_path, source_crs="EPSG:25830"):
    """
    Convierte un GeoJSON a WGS84 (EPSG:4326).
    source_crs: sistema de origen (ej. 'EPSG:25830' para ETRS89 UTM 30N)
    """
    try:
        # Cargar GeoJSON
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir a GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(data['features'])
        gdf = gdf.set_crs(source_crs)
        
        # Reprojectar a WGS84
        gdf = gdf.to_crs("EPSG:4326")
        
        # Guardar como GeoJSON
        gdf.to_file(output_path, driver='GeoJSON')
        print(f"✅ Convertido a WGS84: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    input_file = os.path.join(DATA_PROCESSED, "provinces_clean.geojson")
    output_file = os.path.join(DATA_PROCESSED, "provinces_wgs84.geojson")
    
    # Probar con diferentes CRS comunes (UTM 30N para España peninsular)
    crs_options = ["EPSG:25830", "EPSG:32630", "EPSG:25831", "EPSG:32631"]
    for crs in crs_options:
        if convert_geojson_to_wgs84(input_file, output_file, source_crs=crs):
            print(f"✅ Conversión exitosa usando {crs}")
            break
    else:
        print("❌ No se pudo convertir con ninguno de los CRS probados.")