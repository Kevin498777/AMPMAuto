# data_handler.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DataHandler:
    def __init__(self, file_path):
        self.file_path = file_path
    
    def read_excel(self):
        """Leer y validar archivo Excel"""
        try:
            df = pd.read_excel(self.file_path)
            logger.info(f"Archivo Excel leído exitosamente. {len(df)} filas encontradas.")
            return df
        except Exception as e:
            logger.error(f"Error al leer archivo Excel: {str(e)}")
            return pd.DataFrame()
    
    def validate_data(self, df):
        """Validar estructura y datos del DataFrame"""
        required_columns = ['numero_guia', 'destinatario', 'direccion']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Columnas faltantes en el Excel: {missing_columns}")
            return False
        
        return True