"""Interfaz abstracta para cargadores de datos."""
from abc import ABC, abstractmethod

class BaseLoader(ABC):
    @abstractmethod
    def load(self, year: int):
        pass
