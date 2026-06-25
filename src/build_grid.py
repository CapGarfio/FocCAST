#!/usr/bin/env python3
"""
Construye un grid de prueba (100x100) con valores aleatorios
y lo guarda en data/processed/test_grid.npy
"""
import sys
import os

# Añadir la raíz del proyecto al path para poder importar src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from src.config import DATA_PROCESSED, STATE_GREEN, STATE_RECOVERY, STATE_BURNED, STATE_POPULATION

def generate_test_grid():
    # Crear array aleatorio de 100x100 con valores entre 0 y 3 (4 estados)
    grid = np.random.randint(0, 4, size=(100, 100), dtype=np.int8)
    
    # Forzamos algunos patrones para que no sea completamente ruido:
    grid[0:20, 0:20] = STATE_GREEN          # Esquina sup. izq. Verde
    grid[40:60, 40:60] = STATE_BURNED       # Centro Quemado
    grid[80:100, 80:100] = STATE_POPULATION # Esq. inf. der. Poblacional
    
    # Guardar en la carpeta de datos procesados
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    filepath = os.path.join(DATA_PROCESSED, "test_grid.npy")
    np.save(filepath, grid)
    
    print(f"✅ Grid de prueba generado y guardado en: {filepath}")
    print(f"   Dimensiones: {grid.shape}")
    print(f"   Valores únicos: {np.unique(grid)}")
    print("   (0=Verde, 1=Recuperación, 2=Quemado, 3=Poblacional)")

if __name__ == "__main__":
    generate_test_grid()