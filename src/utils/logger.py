"""
Configuración de logging para el sistema FocCAST.
"""
import logging
import os
from datetime import datetime
from src.config import OUTPUT_DIR

def setup_logger(name: str = "FocCAST", level: int = logging.INFO) -> logging.Logger:
    """
    Configura y retorna un logger con salida en consola y en archivo.
    Los logs se guardan en outputs/logs/foccast_YYYYMMDD.log
    """
    # Crear carpeta de logs si no existe
    log_dir = os.path.join(OUTPUT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Crear el logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitar duplicación de handlers si se llama varias veces
    if logger.hasHandlers():
        logger.handlers.clear()

    # --- Formato ---
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Handler para consola (stdout) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- Handler para archivo (rotación diaria por nombre) ---
    log_filename = f"foccast_{datetime.now().strftime('%Y%m%d')}.log"
    log_path = os.path.join(log_dir, log_filename)
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger