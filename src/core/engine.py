# -*- coding: utf-8 -*-
"""
Motor de simulación del Autómata Celular con probabilidades de ignición.
Incluye contagio vegetativo y fuente antrópica.
"""

import numpy as np
from scipy.ndimage import convolve

class FocCASTEngine:
    def __init__(self, grid_shape, initial_grid=None, 
                 tau_rec=6, tau_verde=24,
                 beta=0.3, rho=0.5,
                 alpha_D=0.4, alpha_S=0.3, alpha_H=0.3, lam=0.1,
                 urban_mask=None):
        """
        grid_shape: (rows, cols)
        initial_grid: array 2D con estados iniciales (si None, todo Verde)
        tau_rec: meses que tarda Quemado -> Recuperación
        tau_verde: meses que tarda Recuperación -> Verde
        beta: coeficiente de transmisibilidad por contagio (0-1)
        rho: factor reductor para estado Recuperación (0-1)
        alpha_D, alpha_S, alpha_H: pesos para distancia, estacionalidad, densidad
        lam: tasa de decaimiento exponencial para distancia
        urban_mask: array booleano con celdas urbanas (para P_antrópico)
        """
        self.rows, self.cols = grid_shape
        self.tau_rec = tau_rec
        self.tau_verde = tau_verde
        self.beta = beta
        self.rho = rho
        self.alpha_D = alpha_D
        self.alpha_S = alpha_S
        self.alpha_H = alpha_H
        self.lam = lam
        self.urban_mask = urban_mask if urban_mask is not None else np.zeros(grid_shape, dtype=bool)

        if initial_grid is not None:
            self.grid = initial_grid.astype(np.int8)
        else:
            self.grid = np.zeros(grid_shape, dtype=np.int8)

        # Contadores de tiempo por celda (meses en el estado actual)
        self.timers = np.zeros(grid_shape, dtype=np.int32)

        # Almacenar historial (opcional)
        self.history = [self.grid.copy()]

        # Precalcular vecindad de Moore (kernel)
        self.kernel = np.ones((3, 3), dtype=np.int8)
        self.kernel[1, 1] = 0  # excluir la celda central

        # Mes actual (para estacionalidad)
        self.current_month = 0

    def set_parameters(self, **kwargs):
        """Actualiza los parámetros del modelo."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        print(f"Parámetros actualizados: {kwargs}")

    def step(self, months=1, seasonality_func=None):
        """
        Avanza la simulación 'months' meses.
        seasonality_func: función que dado un mes (0-11) devuelve un factor (0-1)
        """
        for _ in range(months):
            # Actualizar mes actual (para estacionalidad)
            self.current_month = (self.current_month + 1) % 12
            # Aplicar reglas de transición
            self._apply_rules(seasonality_func)
            self.history.append(self.grid.copy())
        return self.grid

    def _apply_rules(self, seasonality_func=None):
        """
        Aplica las reglas de transición a todo el grid (un paso de tiempo).
        """
        new_grid = self.grid.copy()
        new_timers = self.timers.copy()

        # Calcular P_contagio para cada celda en estado Verde o Recuperación
        P_contagio = self._compute_contagion_prob()

        # Calcular P_antrópico (depende de la estacionalidad)
        if seasonality_func is not None:
            factor_estacional = seasonality_func(self.current_month)
        else:
            # Estacionalidad por defecto: mayor en verano (meses 6,7,8)
            if self.current_month in [6, 7, 8]:
                factor_estacional = 1.0
            elif self.current_month in [5, 9]:
                factor_estacional = 0.7
            else:
                factor_estacional = 0.3

        P_antropico = self._compute_anthropogenic_prob(factor_estacional)

        # Probabilidad conjunta (asumiendo independencia)
        P_ignicion = 1.0 - (1.0 - P_contagio) * (1.0 - P_antropico)

        # Recorrer todas las celdas
        for i in range(self.rows):
            for j in range(self.cols):
                state = self.grid[i, j]
                timer = self.timers[i, j]

                # --- Transiciones de recuperación ---
                if state == 2:  # Quemado
                    timer += 1
                    if timer >= self.tau_rec:
                        new_grid[i, j] = 1  # Pasa a Recuperación
                        new_timers[i, j] = 0
                    else:
                        new_timers[i, j] = timer

                elif state == 1:  # Recuperación
                    timer += 1
                    if timer >= self.tau_verde:
                        new_grid[i, j] = 0  # Pasa a Verde
                        new_timers[i, j] = 0
                    else:
                        new_timers[i, j] = timer

                # --- Posible ignición en Verde o Recuperación ---
                elif state == 0 or state == 1:
                    # La probabilidad de ignición depende del estado (rho para R)
                    if state == 1:
                        prob = P_ignicion[i, j] * self.rho
                    else:
                        prob = P_ignicion[i, j]

                    # Decisión estocástica
                    if np.random.random() < prob:
                        new_grid[i, j] = 2  # Quemado
                        new_timers[i, j] = 0
                    else:
                        # No se quema, pero el timer para recuperación no aplica aquí
                        new_timers[i, j] = 0

                # Poblacional: no cambia
                elif state == 3:
                    new_timers[i, j] = 0

        self.grid = new_grid
        self.timers = new_timers

    def _compute_contagion_prob(self):
        """Calcula P_contagio para cada celda usando convolución."""
        # Contar vecinos quemados (estado 2)
        burned = (self.grid == 2).astype(np.int8)
        neighbors_burned = convolve(burned, self.kernel, mode='constant', cval=0)
        # P_contagio = 1 - (1 - beta)^(n_quemados)
        P_contagio = 1.0 - (1.0 - self.beta) ** neighbors_burned
        return P_contagio

    def _compute_anthropogenic_prob(self, factor_estacional):
        """
        Calcula P_antrópico para cada celda.
        f_D = sum_{urban} exp(-lam * distancia)
        Se simplifica usando una máscara urbana y convolución con kernel exponencial.
        """
        # Para simplificar, usamos una aproximación: distancia a la celda urbana más cercana
        # En una implementación real, se podría usar una transformada de distancia
        # Aquí usamos una convolución con un kernel gaussiano para simular el decaimiento
        from scipy.ndimage import distance_transform_edt

        # Distancia a la celda urbana más cercana
        if np.any(self.urban_mask):
            dist = distance_transform_edt(~self.urban_mask)
            f_D = np.exp(-self.lam * dist)
        else:
            f_D = np.zeros_like(self.grid, dtype=float)

        # Densidad poblacional (H) - por ahora constante o basada en urban_mask
        H = self.urban_mask.astype(float)  # 1 si urbano, 0 si no

        # Factor estacional S(t) ya está en factor_estacional
        P_antropico = 1.0 - (1.0 - self.alpha_D * f_D) * \
                             (1.0 - self.alpha_S * factor_estacional) * \
                             (1.0 - self.alpha_H * H)
        return P_antropico

    def get_grid_at_time(self, month):
        """Retorna el grid en un mes específico (si se ha almacenado el historial)."""
        if month < len(self.history):
            return self.history[month]
        else:
            # Si no tenemos historial, ejecutamos pasos hasta alcanzar ese mes
            current_len = len(self.history)
            for _ in range(current_len, month + 1):
                self.step()
            return self.history[month]

    def reset(self, grid=None):
        """Reinicia la simulación con un nuevo grid inicial."""
        if grid is not None:
            self.grid = grid.astype(np.int8)
        else:
            self.grid = np.zeros((self.rows, self.cols), dtype=np.int8)
        self.timers = np.zeros_like(self.grid, dtype=np.int32)
        self.history = [self.grid.copy()]
        self.current_month = 0