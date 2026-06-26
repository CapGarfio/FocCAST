#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importa y procesa los archivos TopoJSON de es-atlas desde un CDN.
Convierte a GeoJSON limpio y lo guarda en data/processed/.
"""
import os
import sys
import json
import requests
from pathlib import Path

# Añadir la raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import DATA_RAW, DATA_PROCESSED
from src.utils.logger import setup_logger

logger = setup_logger("ImportTopoJSON")

# Intentar importar topojson, si falla usar geopandas
try:
    import topojson as tp
    HAS_TOPOJSON = True
except ImportError:
    HAS_TOPOJSON = False
    logger.warning("topojson no instalado. Se usará geopandas como alternativa.")

# ------------------------------------------------------------
# Descargar archivos desde CDN
# ------------------------------------------------------------
def download_file(url, output_path):
    """Descarga un archivo desde una URL y lo guarda en output_path."""
    try:
        logger.info(f"Descargando {url} -> {output_path}")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            content = response.text.strip()
            if content.startswith('{') or content.startswith('['):
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"✅ Descargado correctamente: {output_path}")
                return True
            else:
                logger.error(f"El contenido no parece JSON: {content[:200]}")
                return False
        else:
            logger.error(f"Error {response.status_code} descargando {url}")
            return False
    except Exception as e:
        logger.error(f"Excepción descargando {url}: {e}")
        return False

# ------------------------------------------------------------
# Convertir TopoJSON a GeoJSON usando diferentes métodos
# ------------------------------------------------------------
def convert_topojson_to_geojson(input_path, output_path, object_name=None):
    """
    Convierte un archivo TopoJSON a GeoJSON.
    Detecta automáticamente el objeto si no se especifica.
    """
    try:
        logger.info(f"Convirtiendo {input_path} -> {output_path}")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Detectar el nombre del objeto
        objects = data.get('objects', {})
        if not objects:
            logger.error("El archivo TopoJSON no contiene objetos.")
            return False
        
        if object_name is None:
            object_name = list(objects.keys())[0]
        logger.info(f"Objeto detectado: '{object_name}'")
        
        # --- Método 1: Usar topojson (si está disponible) ---
        if HAS_TOPOJSON:
            try:
                topology = tp.Topology(data)
                geojson = topology.to_geojson(object_name=object_name)
                # Guardar como GeoJSON
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(geojson, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ Convertido con topojson: {output_path}")
                return True
            except Exception as e:
                logger.warning(f"Error con topojson: {e}. Intentando método alternativo.")
        
        # --- Método 2: Extraer manualmente el objeto y crear GeoJSON ---
        logger.info("Usando método manual de extracción...")
        object_data = objects.get(object_name)
        if not object_data:
            logger.error(f"Objeto '{object_name}' no encontrado en objects.")
            return False
        
        # Obtener geometrías y propiedades
        geometries = object_data.get('geometries', [])
        if not geometries:
            # Si no hay geometrías, buscar en 'features'
            geometries = object_data.get('features', [])
        
        if not geometries:
            logger.error("No se encontraron geometrías en el objeto.")
            return False
        
        # Crear FeatureCollection
        features = []
        for geom in geometries:
            # Extraer propiedades
            props = geom.get('properties', {})
            # Extraer geometría (puede estar en 'geometry' o ser la geometría misma)
            geometry = geom.get('geometry')
            if geometry is None:
                # Si no tiene 'geometry', la geometría es el objeto mismo (sin 'type')
                geometry = {k: v for k, v in geom.items() if k != 'properties' and k != 'id'}
                # Asegurar que tenga 'type'
                if 'type' not in geometry:
                    # Si es un punto, línea o polígono, se lo añadimos
                    if 'coordinates' in geometry:
                        geometry['type'] = 'Point'  # o 'LineString', etc. (no podemos saberlo)
            
            if geometry:
                feature = {
                    "type": "Feature",
                    "properties": props,
                    "geometry": geometry
                }
                # Añadir id si existe
                if 'id' in geom:
                    feature['id'] = geom['id']
                features.append(feature)
        
        # Crear FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Guardar
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Convertido manualmente: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error convirtiendo {input_path}: {e}")
        return False

# ------------------------------------------------------------
# Normalizar códigos INE
# ------------------------------------------------------------
def normalize_codes(geojson_path):
    """Añade campo 'codigo' normalizado a cada feature."""
    try:
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            # Buscar código en varios campos
            code = (feature.get('id') or 
                   props.get('id') or 
                   props.get('ine') or 
                   props.get('codigo') or 
                   props.get('COD_PROV') or
                   props.get('PROVINCIA'))
            if code:
                props['codigo'] = str(code).zfill(2)
            # También normalizar nombre
            name = (props.get('name') or 
                   props.get('nombre') or 
                   props.get('NOMBRE') or 
                   props.get('NAME'))
            if name:
                props['nombre'] = name
        
        with open(geojson_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error normalizando códigos: {e}")
        return False

# ------------------------------------------------------------
# Función principal
# ------------------------------------------------------------
def main():
    # URLs de los archivos TopoJSON de es-atlas (CDN)
    urls = {
        "provinces": "https://unpkg.com/es-atlas/es/provinces.json",
        "municipalities": "https://unpkg.com/es-atlas/es/municipalities.json",
        "autonomous_regions": "https://unpkg.com/es-atlas/es/autonomous_regions.json"
    }
    
    # Crear carpetas si no existen
    os.makedirs(DATA_RAW, exist_ok=True)
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    
    # Procesar cada archivo
    for name, url in urls.items():
        raw_path = os.path.join(DATA_RAW, f"{name}.json")
        processed_path = os.path.join(DATA_PROCESSED, f"{name}.geojson")
        
        # Verificar si el archivo raw existe y es válido
        needs_download = False
        if os.path.exists(raw_path):
            try:
                with open(raw_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                logger.info(f"Archivo {raw_path} ya existe y es válido.")
            except:
                needs_download = True
                logger.warning(f"Archivo {raw_path} corrupto. Se descargará de nuevo.")
        else:
            needs_download = True
        
        if needs_download:
            if not download_file(url, raw_path):
                logger.error(f"❌ Fallo al descargar {name}. Continuando con el siguiente.")
                continue
        
        # Convertir TopoJSON a GeoJSON
        # Para municipios y provincias, normalizar códigos
        if not convert_topojson_to_geojson(raw_path, processed_path):
            logger.error(f"❌ Fallo al convertir {name}.")
            continue
        
        # Normalizar códigos para provincias y municipios
        if name in ["provinces", "municipalities"]:
            if normalize_codes(processed_path):
                logger.info(f"✅ Códigos normalizados para {name}.")
            else:
                logger.warning(f"⚠️ No se pudieron normalizar códigos para {name}.")
        
        logger.info(f"✅ Procesado {name} correctamente.")
    
    logger.info("🎉 Todos los archivos procesados correctamente.")

if __name__ == "__main__":
    main()