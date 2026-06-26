#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga el contorno de una provincia desde OpenStreetMap usando OSMnx.
Uso: python scripts/download_province_contour.py [codigo_ine]
Ejemplo: python scripts/download_province_contour.py 46  # Valencia
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import osmnx as ox
import geopandas as gpd
import json
from src.config import DATA_RAW

def download_province_contour(province_code):
    """
    Descarga el contorno de la provincia desde OSM y lo guarda como GeoJSON.
    """
    # Mapeo de códigos INE a nombres de provincias en español (para OSM)
    # Esto es necesario porque OSM usa nombres, no códigos
    province_names = {
        "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería",
        "05": "Ávila", "06": "Badajoz", "07": "Islas Baleares", "08": "Barcelona",
        "09": "Burgos", "10": "Cáceres", "11": "Cádiz", "12": "Castellón",
        "13": "Ciudad Real", "14": "Córdoba", "15": "La Coruña", "16": "Cuenca",
        "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Guipúzcoa",
        "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León",
        "25": "Lleida", "26": "La Rioja", "27": "Lugo", "28": "Madrid",
        "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense",
        "33": "Asturias", "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra",
        "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
        "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona",
        "44": "Teruel", "45": "Toledo", "46": "Valencia", "47": "Valladolid",
        "48": "Vizcaya", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta", "52": "Melilla"
    }
    
    province_name = province_names.get(province_code)
    if not province_name:
        print(f"Error: Código {province_code} no reconocido.")
        return False
    
    print(f"Descargando contorno de {province_name} desde OpenStreetMap...")
    try:
        # Descargar el límite administrativo de la provincia (admin_level=6 en España)
        gdf = ox.geocode_to_gdf(f"{province_name}, España", which_result=1)
        if gdf.empty:
            print(f"No se encontró {province_name} en OSM.")
            return False
        
        # Guardar como GeoJSON
        os.makedirs(DATA_RAW, exist_ok=True)
        output_path = os.path.join(DATA_RAW, f"provincia_{province_code}.geojson")
        gdf.to_file(output_path, driver='GeoJSON')
        print(f"Contorno guardado en {output_path}")
        return True
    except Exception as e:
        print(f"Error descargando contorno: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        download_province_contour(sys.argv[1])
    else:
        print("Uso: python download_province_contour.py [codigo_ine]")