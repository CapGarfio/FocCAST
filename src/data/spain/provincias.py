# -*- coding: utf-8 -*-
"""
Datos de provincias de España.
Códigos INE, nombres y bounding boxes aproximados (para descarga de CORINE).
"""
import os
import json

# Bounding boxes aproximados para cada provincia (min_lon, min_lat, max_lon, max_lat)
# Estos valores son orientativos y cubren toda la provincia.
# Se pueden refinar con datos más precisos si es necesario.
PROVINCIAS = {
    "01": {"nombre": "Álava", "bbox": [-3.3, 42.7, -2.3, 43.1]},
    "02": {"nombre": "Albacete", "bbox": [-2.6, 38.1, -1.0, 39.5]},
    "03": {"nombre": "Alicante", "bbox": [-1.0, 37.8, 0.3, 38.8]},
    "04": {"nombre": "Almería", "bbox": [-2.7, 36.6, -1.5, 37.8]},
    "05": {"nombre": "Ávila", "bbox": [-5.2, 40.1, -4.2, 41.0]},
    "06": {"nombre": "Badajoz", "bbox": [-7.2, 37.8, -5.1, 39.5]},
    "07": {"nombre": "Islas Baleares", "bbox": [1.0, 38.5, 4.5, 40.0]},
    "08": {"nombre": "Barcelona", "bbox": [1.7, 41.0, 2.8, 42.0]},
    "09": {"nombre": "Burgos", "bbox": [-4.3, 41.7, -2.7, 43.2]},
    "10": {"nombre": "Cáceres", "bbox": [-7.0, 38.9, -5.3, 40.6]},
    "11": {"nombre": "Cádiz", "bbox": [-6.4, 35.9, -5.0, 37.0]},
    "12": {"nombre": "Castellón", "bbox": [-0.7, 39.7, 0.5, 40.9]},
    "13": {"nombre": "Ciudad Real", "bbox": [-4.8, 38.0, -2.8, 39.6]},
    "14": {"nombre": "Córdoba", "bbox": [-5.3, 37.4, -3.9, 38.7]},
    "15": {"nombre": "La Coruña", "bbox": [-9.2, 42.7, -7.8, 43.8]},
    "16": {"nombre": "Cuenca", "bbox": [-2.7, 39.2, -1.4, 40.7]},
    "17": {"nombre": "Girona", "bbox": [1.7, 41.6, 3.4, 42.5]},
    "18": {"nombre": "Granada", "bbox": [-4.0, 36.5, -2.3, 37.9]},
    "19": {"nombre": "Guadalajara", "bbox": [-3.5, 40.2, -2.0, 41.5]},
    "20": {"nombre": "Guipúzcoa", "bbox": [-2.5, 43.0, -1.7, 43.4]},
    "21": {"nombre": "Huelva", "bbox": [-7.3, 36.8, -6.0, 38.0]},
    "22": {"nombre": "Huesca", "bbox": [-0.5, 41.8, 1.0, 43.0]},
    "23": {"nombre": "Jaén", "bbox": [-4.0, 37.3, -2.7, 38.5]},
    "24": {"nombre": "León", "bbox": [-6.5, 42.0, -4.8, 43.3]},
    "25": {"nombre": "Lleida", "bbox": [0.2, 41.2, 2.0, 42.9]},
    "26": {"nombre": "La Rioja", "bbox": [-3.1, 41.9, -1.7, 42.8]},
    "27": {"nombre": "Lugo", "bbox": [-7.7, 42.4, -6.5, 43.8]},
    "28": {"nombre": "Madrid", "bbox": [-4.0, 39.8, -3.0, 41.0]},
    "29": {"nombre": "Málaga", "bbox": [-5.4, 36.3, -3.8, 37.2]},
    "30": {"nombre": "Murcia", "bbox": [-2.0, 37.2, -0.8, 38.6]},
    "31": {"nombre": "Navarra", "bbox": [-2.3, 41.8, -0.9, 43.2]},
    "32": {"nombre": "Ourense", "bbox": [-8.2, 41.7, -6.7, 42.5]},
    "33": {"nombre": "Asturias", "bbox": [-6.9, 43.0, -4.5, 43.7]},
    "34": {"nombre": "Palencia", "bbox": [-4.8, 41.8, -4.0, 42.8]},
    "35": {"nombre": "Las Palmas", "bbox": [-15.9, 27.5, -13.0, 29.5]},
    "36": {"nombre": "Pontevedra", "bbox": [-8.9, 41.8, -8.0, 42.7]},
    "37": {"nombre": "Salamanca", "bbox": [-6.8, 40.2, -5.0, 41.2]},
    "38": {"nombre": "Santa Cruz de Tenerife", "bbox": [-18.2, 27.3, -16.0, 29.0]},
    "39": {"nombre": "Cantabria", "bbox": [-4.5, 42.7, -3.0, 43.5]},
    "40": {"nombre": "Segovia", "bbox": [-4.4, 40.8, -3.5, 41.6]},
    "41": {"nombre": "Sevilla", "bbox": [-6.5, 36.9, -5.0, 38.0]},
    "42": {"nombre": "Soria", "bbox": [-3.0, 41.1, -1.8, 42.2]},
    "43": {"nombre": "Tarragona", "bbox": [0.1, 40.4, 1.8, 41.7]},
    "44": {"nombre": "Teruel", "bbox": [-1.5, 39.8, 0.5, 41.0]},
    "45": {"nombre": "Toledo", "bbox": [-4.8, 39.2, -3.0, 40.3]},
    "46": {"nombre": "Valencia", "bbox": [-1.5, 38.5, 0.5, 40.5]},
    "47": {"nombre": "Valladolid", "bbox": [-5.2, 41.0, -4.0, 42.0]},
    "48": {"nombre": "Vizcaya", "bbox": [-3.2, 43.0, -2.4, 43.5]},
    "49": {"nombre": "Zamora", "bbox": [-6.8, 41.2, -5.0, 42.2]},
    "50": {"nombre": "Zaragoza", "bbox": [-1.8, 41.0, 0.5, 42.8]},
    "51": {"nombre": "Ceuta", "bbox": [-5.4, 35.8, -5.2, 35.9]},
    "52": {"nombre": "Melilla", "bbox": [-2.98, 35.28, -2.92, 35.32]},
}

def get_province_list():
    """Retorna lista de tuplas (codigo, nombre) ordenadas por nombre."""
    return sorted([(code, data["nombre"]) for code, data in PROVINCIAS.items()], key=lambda x: x[1])

def get_province_bbox(code):
    """Retorna el bounding box para una provincia dada su código INE."""
    return PROVINCIAS.get(code, {}).get("bbox", None)