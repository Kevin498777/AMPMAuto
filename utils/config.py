# utils/config.py
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, env_file=".env"):
        self.env_file = env_file
        self.load_environment()
    
    def load_environment(self):
        """Carga las variables de entorno desde el archivo .env"""
        if os.path.exists(self.env_file):
            load_dotenv(self.env_file)
            logger.info("Variables de entorno cargadas desde .env")
        else:
            logger.warning("No se encontró el archivo .env. Se usarán variables del sistema.")
    
    def get(self, key, default=None):
        """Obtiene el valor de una variable de entorno"""
        return os.getenv(key, default)
    
    # Credenciales específicas para AMPM
    @property
    def ampm_username(self):
        return self.get('AMPM_USERNAME')
    
    @property
    def ampm_password(self):
        return self.get('AMPM_PASSWORD')
    
    @property
    def ampm_url(self):
        return self.get('AMPM_URL', 'https://portal.ampm.com.mx')  # URL por defecto
    
    # Configuración de la aplicación
    @property
    def headless_mode(self):
        return self.get('HEADLESS_MODE', 'True').lower() == 'true'
    
    @property
    def timeout(self):
        return int(self.get('TIMEOUT', '30'))
    
    @property
    def max_retries(self):
        return int(self.get('MAX_RETRIES', '3'))
    
    # Configuración de reportes
    @property
    def generate_pdf_reports(self):
        return self.get('GENERATE_PDF_REPORTS', 'True').lower() == 'true'
    
    @property
    def generate_excel_reports(self):
        return self.get('GENERATE_EXCEL_REPORTS', 'True').lower() == 'true'

# Instancia global para uso fácil
config = ConfigManager()

# Funciones de conveniencia
def get_ampm_credentials():
    """Obtiene las credenciales de AMPM"""
    username = config.ampm_username
    password = config.ampm_password
    
    if not username or not password:
        logger.warning("Credenciales de AMPM no configuradas en el archivo .env")
    
    return username, password

def get_application_settings():
    """Obtiene la configuración de la aplicación"""
    return {
        'headless': config.headless_mode,
        'timeout': config.timeout,
        'max_retries': config.max_retries,
        'ampm_url': config.ampm_url
    }