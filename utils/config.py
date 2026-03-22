# utils/config.py - MODIFICADO PARA USAR APPDATA EN WINDOWS
import os
import sys
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

def get_app_data_path():
    """Obtener ruta en AppData/Local para archivos de usuario"""
    try:
        if os.name == 'nt':  # Windows
            app_data = os.getenv('LOCALAPPDATA')
            if app_data:
                app_path = os.path.join(app_data, 'AMPMAuto')
                os.makedirs(app_path, exist_ok=True)
                return app_path
        # Fallback para Linux/Mac y casos de error
        fallback_path = os.path.join(os.path.expanduser('~'), '.ampmauto')
        os.makedirs(fallback_path, exist_ok=True)
        return fallback_path
    except Exception as e:
        logger.warning(f"No se pudo crear directorio en AppData: {e}")
        # Último fallback: directorio actual
        return os.path.dirname(os.path.abspath(sys.argv[0]))

class ConfigManager:
    def __init__(self, env_file=None):
        # Determinar la ruta del archivo .env
        if env_file is None:
            # Primero, intentar usar la ruta en AppData
            app_data_dir = get_app_data_path()
            self.env_file = os.path.join(app_data_dir, ".env")
            
            # Si no existe en AppData, buscar en el directorio de la aplicación
            if not os.path.exists(self.env_file):
                app_dir_env = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".env")
                if os.path.exists(app_dir_env):
                    # Si existe en el directorio de la aplicación, copiarlo a AppData
                    try:
                        import shutil
                        shutil.copy2(app_dir_env, self.env_file)
                        logger.info(f"Copiado .env desde {app_dir_env} a {self.env_file}")
                    except Exception as e:
                        logger.warning(f"No se pudo copiar .env: {e}")
                        # Usar el de la aplicación como respaldo
                        self.env_file = app_dir_env
        else:
            self.env_file = env_file
        
        self.load_environment()
        logger.info(f"Usando archivo .env en: {self.env_file}")
    
    def load_environment(self):
        """Carga las variables de entorno desde el archivo .env"""
        if os.path.exists(self.env_file):
            load_dotenv(dotenv_path=self.env_file, override=True)
            logger.info(f"Variables de entorno cargadas desde {self.env_file}")
        else:
            logger.warning(f"No se encontró el archivo .env en {self.env_file}. Se usarán variables del sistema.")
    
    def get(self, key, default=None):
        """Obtiene el valor de una variable de entorno"""
        return os.getenv(key, default)
    
    # Credenciales específicas para AMPM
    @property
    def ampm_convenio(self):
        return self.get('AMPM_CONVENIO', '0')
    
    @property
    def ampm_username(self):
        return self.get('AMPM_USERNAME')
    
    @property
    def ampm_password(self):
        return self.get('AMPM_PASSWORD')
    
    @property
    def ampm_url(self):
        return self.get('AMPM_URL', 'https://convenios.grupoampm.com/Convenio/Login?returnUrl=/')
    
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
    
    # MÉTODO NUEVO MEJORADO: Guardar credenciales Y TODAS LAS VARIABLES
    def save_credentials(self, convenio, username, password, url=None):
        """Guarda las credenciales en el archivo .env - VERSIÓN MEJORADA"""
        try:
            # Asegurar que el directorio existe
            os.makedirs(os.path.dirname(self.env_file), exist_ok=True)
            
            # Leer todo el archivo .env actual si existe
            existing_vars = {}
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Manejar líneas con comentarios al final
                            if '#' in line:
                                line = line.split('#')[0].strip()
                            if '=' in line:
                                key, value = line.split('=', 1)
                                existing_vars[key.strip()] = value.strip()
            
            # Variables a actualizar/agregar
            variables_to_update = {
                'AMPM_CONVENIO': convenio,
                'AMPM_USERNAME': username,
                'AMPM_PASSWORD': password
            }
            
            # Agregar URL si se proporciona
            if url:
                variables_to_update['AMPM_URL'] = url
            
            # Variables de configuración existentes que debemos preservar
            config_variables = [
                'HEADLESS_MODE',
                'TIMEOUT',
                'MAX_RETRIES',
                'GENERATE_PDF_REPORTS',
                'GENERATE_EXCEL_REPORTS'
            ]
            
            # Preservar valores existentes de configuración
            for var in config_variables:
                if var in existing_vars:
                    variables_to_update[var] = existing_vars[var]
                else:
                    # Si no existe, usar el valor actual de la propiedad
                    current_value = self.get(var)
                    if current_value:
                        variables_to_update[var] = current_value
            
            # Crear nuevo contenido del archivo .env
            new_content = []
            
            # Primero agregar comentarios y variables actualizadas
            new_content.append("# Credenciales REALES de AMPM (USAR TUS DATOS REALES)\n")
            for key in ['AMPM_CONVENIO', 'AMPM_USERNAME', 'AMPM_PASSWORD', 'AMPM_URL']:
                if key in variables_to_update:
                    new_content.append(f"{key}={variables_to_update[key]}\n")
            
            new_content.append("\n# Configuración de la aplicación\n")
            for key in ['HEADLESS_MODE', 'TIMEOUT', 'MAX_RETRIES']:
                if key in variables_to_update:
                    new_content.append(f"{key}={variables_to_update[key]}\n")
            
            new_content.append("\n# Configuración de reportes\n")
            for key in ['GENERATE_PDF_REPORTS', 'GENERATE_EXCEL_REPORTS']:
                if key in variables_to_update:
                    new_content.append(f"{key}={variables_to_update[key]}\n")
            
            # Escribir el archivo
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(new_content)
            
            # Recargar las variables de entorno
            self.load_environment()
            logger.info(f"✅ Credenciales actualizadas en el archivo .env: {self.env_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al guardar credenciales en {self.env_file}: {str(e)}")
            return False

# Instancia global para uso fácil
config = ConfigManager()

# Funciones de conveniencia
def get_ampm_credentials():
    """Obtiene las credenciales de AMPM"""
    convenio = config.ampm_convenio
    username = config.ampm_username
    password = config.ampm_password
    
    if not username or not password:
        logger.warning("Credenciales de AMPM no configuradas en el archivo .env")
    
    return convenio, username, password

def get_application_settings():
    """Obtiene la configuración de la aplicación"""
    return {
        'headless': config.headless_mode,
        'timeout': config.timeout,
        'max_retries': config.max_retries,
        'ampm_url': config.ampm_url
    }