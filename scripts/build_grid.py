#!/usr/bin/env python3
"""
Genera un grid sintético de 100x100 que imita la silueta de la provincia de Valencia
para pruebas visuales. Guarda en data/processed/test_grid.npy
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
from src.config import DATA_PROCESSED, STATE_GREEN, STATE_RECOVERY, STATE_BURNED, STATE_POPULATION

def generate_test_grid():
    # Crear grid de 100x100 inicializado a STATE_GREEN (0)
    grid = np.full((100, 100), STATE_GREEN, dtype=np.int8)
    
    # Definir coordenadas relativas (fila, columna) para la provincia
    # Simulamos que el grid cubre la zona entre 38.5N-40.5N y 1.5W-0.5E
    # El mar está al este (columnas altas) y el interior al oeste
    
    # 1. MAR (Mediterráneo): lo representamos con un valor especial (4) aunque no es un estado oficial
    # Para distinguirlo visualmente, usaremos un color azul oscuro en el mapa más adelante.
    # Pero como nuestro mapa solo pinta los 4 estados, no lo pintaremos; lo dejaremos como fondo.
    # En su lugar, haremos que las celdas del mar sean STATE_BURNED (rojo) para que se vean distintas.
    # Esto es solo para la demo.
    
    # 2. COSTA: definimos una línea de costa aproximada (fila, columna)
    # Para simplificar, usamos una curva suave
    coast = []
    for row in range(20, 80):  # de norte a sur
        # La costa avanza hacia el este según la latitud (más al este en el sur)
        col = int(40 + 20 * np.sin((row - 50) / 30 * np.pi) + 10 * (row - 50) / 30)
        coast.append((row, col))
    
    # 3. PINTAMOS EL MAR (al este de la costa) como STATE_BURNED (rojo)
    for row in range(100):
        for col in range(100):
            # Determinamos si la celda está al este de la costa (mar)
            # Para cada fila, encontramos la columna de la costa más cercana
            coast_col = None
            for r, c in coast:
                if row == r:
                    coast_col = c
                    break
            if coast_col is None:
                # Interpolamos para filas sin costa definida
                # Usamos la media de las dos más cercanas
                pass
            else:
                if col > coast_col:
                    grid[row, col] = STATE_BURNED  # mar -> rojo (quemado)
    
    # 4. CIUDAD DE VALENCIA: zona urbana (STATE_POPULATION = 3) alrededor del centro
    # Aprox. fila 55, columna 55
    for row in range(48, 62):
        for col in range(48, 62):
            if (row-55)**2 + (col-55)**2 < 100:  # círculo
                grid[row, col] = STATE_POPULATION
    
    # 5. ZONA DE RECUPERACIÓN (naranja) en el interior (montaña)
    for row in range(20, 40):
        for col in range(10, 30):
            if (row-30)**2 + (col-20)**2 < 150:
                grid[row, col] = STATE_RECOVERY
    
    # 6. BOSQUE VERDE en el resto (ya está por defecto)
    # Pero añadimos algunas manchas de quemado (STATE_BURNED) aleatorias
    np.random.seed(42)  # para reproducibilidad
    for _ in range(50):
        r = np.random.randint(10, 90)
        c = np.random.randint(10, 90)
        if grid[r, c] == STATE_GREEN:
            grid[r, c] = STATE_BURNED
    
    # Guardar
    os.makedirs(DATA_PROCESSED, exist_ok=True)
    filepath = os.path.join(DATA_PROCESSED, "test_grid.npy")
    np.save(filepath, grid)
    
    print(f"✅ Grid sintético con silueta de Valencia generado en: {filepath}")
    print(f"   Dimensiones: {grid.shape}")
    print(f"   Valores únicos: {np.unique(grid)}")
    print("   (0=Verde, 1=Recuperación, 2=Quemado, 3=Poblacional)")
    print("   Nota: el mar se ha pintado como 'Quemado' (rojo) para distinguirlo visualmente.")

if __name__ == "__main__":
    generate_test_grid()