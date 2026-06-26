#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para preprocesar los archivos TopoJSON descargados de es-atlas.
Lee los archivos desde data/raw/, los convierte a GeoJSON, limpia los campos
y guarda versiones procesadas en data/processed/.
"""
import sys
import os
import json

# Añadir la raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import DATA_RAW, DATA_PROCESSED
from src.utils.logger import setup_logger

logger = setup_logger("PreprocessGeoData")

def convert_topojson_to_geojson(input_path, output_path, id_field='id'):
    """
    Convierte un archivo TopoJSON a GeoJSON limpio.
    """
    try:
        import topojson as tp
    except ImportError:
        logger.error("La librería 'topojson' no está instalada. Ejecuta: pip install topojson")
        return False

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir a GeoJSON
        topology = tp.Topology(data)
        geojson_data = topology.to_geojson()
        
        # Limpiar los features: asegurar que tengan id y nombre
        features = geojson_data.get('features', [])
        cleaned_features = []
        for feature in features:
            # Obtener el id (código INE) desde el campo 'id' del feature o desde properties
            feature_id = feature.get('id')
            if feature_id is None:
                # Si no tiene id, intentar obtenerlo de properties
                props = feature.get('properties', {})
                feature_id = props.get('id') or props.get('codigo') or props.get('CODE')
            
            if feature_id is not None:
                # Asegurar que el id se guarde como string con dos dígitos
                feature['id'] = str(feature_id).zfill(2)
            else:
                logger.warning(f"Feature sin id encontrado: {feature}")
                continue
            
            # Asegurar que el nombre esté en properties
            props = feature.get('properties', {})
            if 'name' not in props:
                # Buscar nombre en otros campos comunes
                name = props.get('NOMBRE') or props.get('nombre') or props.get('NAME')
                if name:
                    props['name'] = name
                else:
                    logger.warning(f"Feature sin nombre: {feature_id}")
                    props['name'] = f"Provincia {feature_id}"
            
            # Guardar solo los campos esenciales (id y name)
            feature['properties'] = {'name': props.get('name')}
            cleaned_features.append(feature)
        
        # Reemplazar features con la versión limpia
        geojson_data['features'] = cleaned_features
        
        # Guardar el GeoJSON limpio
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ GeoJSON procesado guardado en: {output_path}")
        logger.info(f"   Total de features: {len(cleaned_features)}")
        return True

    except Exception as e:
        logger.error(f"Error procesando {input_path}: {e}")
        return False

def preprocess_all():
    """Procesa todos los archivos descargados."""
    # Definir los archivos a procesar
    files_to_process = [
        ('provinces.json', 'provinces_clean.geojson'),
        ('municipalities.json', 'municipalities_clean.geojson'),
        ('autonomous_regions.json', 'regions_clean.geojson')
    ]
    
    for input_name, output_name in files_to_process:
        input_path = os.path.join(DATA_RAW, input_name)
        output_path = os.path.join(DATA_PROCESSED, output_name)
        
        if not os.path.exists(input_path):
            logger.warning(f"Archivo {input_name} no encontrado en {DATA_RAW}. Omitiendo.")
            continue
        
        logger.info(f"Procesando {input_name} -> {output_name}")
        success = convert_topojson_to_geojson(input_path, output_path)
        if success:
            logger.info(f"✅ {input_name} procesado correctamente.")
        else:
            logger.error(f"❌ Fallo al procesar {input_name}.")

if __name__ == "__main__":
    preprocess_all()