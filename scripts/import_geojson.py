#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga directamente un archivo GeoJSON de provincias de España
desde un repositorio fiable y lo guarda en data/processed/.
"""
import os
import sys
import json
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import DATA_PROCESSED
from src.utils.logger import setup_logger

logger = setup_logger("ImportGeoJSON")

def download_geojson(url, output_path):
    try:
        logger.info(f"Descargando {url} -> {output_path}")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if 'features' in data:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ GeoJSON guardado en {output_path}")
                return True
            else:
                logger.error("El archivo no contiene 'features'")
                return False
        else:
            logger.error(f"Error {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Excepción: {e}")
        return False

def main():
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    
    # Fuentes alternativas de GeoJSON de provincias de España
    urls = [
        "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/spain-provinces.geojson",
        "https://gist.githubusercontent.com/josemamira/3af52a4698d42b3f676fbc23f807a605/raw/provincias_spain.geojson"
    ]
    
    for url in urls:
        output_path = os.path.join(DATA_PROCESSED, "provinces.geojson")
        if download_geojson(url, output_path):
            logger.info("✅ Provincias importadas correctamente.")
            return
    
    logger.error("❌ No se pudo descargar desde ninguna fuente.")

if __name__ == "__main__":
    main()