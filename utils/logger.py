# utils/logger.py - VERSIÓN COMPLETA CORREGIDA
import logging
import os
from datetime import datetime
import sys

def get_app_data_path():
    """Obtener ruta en AppData/Local para archivos de usuario"""
    try:
        # Para Windows: usar AppData/Local
        if os.name == 'nt':  # Windows
            app_data = os.getenv('LOCALAPPDATA')
            if app_data:
                app_path = os.path.join(app_data, 'AMPMAuto')
                os.makedirs(app_path, exist_ok=True)
                return app_path
        
        # Para otros sistemas o fallback
        return os.path.join(os.path.expanduser('~'), '.ampmauto')
    except:
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def setup_logger(name=__name__, log_level=logging.INFO):
    """Configura el logger para la aplicación - VERSIÓN CORREGIDA"""
    
    # Usar carpeta con permisos de escritura
    base_dir = get_app_data_path()
    log_dir = os.path.join(base_dir, "logs")
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
    
    try:
        # Handler para archivo - en carpeta con permisos
        log_file = os.path.join(log_dir, f"ampmauto_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logs guardados en: {log_file}")
    except Exception as e:
        # Fallback: solo consola si no se puede escribir archivo
        logger.warning(f"No se pudo crear archivo de log: {e}")
    
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