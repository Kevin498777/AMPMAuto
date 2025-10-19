# utils/logger.py
import logging
import os
from datetime import datetime

def setup_logger(name=__name__, log_level=logging.INFO):
    """Configura el logger para la aplicación"""
    
    # Crear el directorio de logs si no existe
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurar el logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Evitar logs duplicados
    if logger.handlers:
        logger.handlers.clear()
    
    # Formato del log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para archivo
    log_file = os.path.join(log_dir, f"ampmauto_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Configuración de logs específicos para diferentes módulos
def get_module_logger(module_name):
    """Obtiene un logger específico para un módulo"""
    return setup_logger(f"ampmauto.{module_name}")

# Logger preconfigurado para uso rápido
app_logger = setup_logger("AMPMAuto")

# Funciones de conveniencia para logging
def log_info(message):
    """Registra un mensaje informativo"""
    app_logger.info(message)

def log_error(message, exc_info=False):
    """Registra un mensaje de error"""
    app_logger.error(message, exc_info=exc_info)

def log_warning(message):
    """Registra un mensaje de advertencia"""
    app_logger.warning(message)

def log_debug(message):
    """Registra un mensaje de depuración"""
    app_logger.debug(message)