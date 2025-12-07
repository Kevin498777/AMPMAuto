# data_handler.py
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# DataHandler mejorado - BUSCA GUÍAS EN TODAS LAS COLUMNAS
class DataHandler:
    """Manejador de datos para archivos Excel - VERSIÓN MEJORADA CON BÚSQUEDA EN TODAS LAS COLUMNAS"""
    
    def __init__(self, excel_file_path):
        self.excel_file_path = excel_file_path
    
    def read_excel(self):
        """Leer archivo Excel y extraer guías de TODAS las columnas - VERSIÓN ROBUSTA"""
        try:
            df = pd.read_excel(self.excel_file_path)
            logger.info(f"📊 Archivo Excel cargado: {len(df)} filas, {len(df.columns)} columnas")
            logger.info(f"📋 Columnas detectadas: {list(df.columns)}")
            
            # ✅ BUSCAR GUÍAS EN TODAS LAS COLUMNAS
            todas_las_guias = self._buscar_guias_en_todas_las_columnas(df)
            
            if todas_las_guias:
                # Crear DataFrame con las guías encontradas
                df_final = pd.DataFrame({'numero_guia': todas_las_guias})
                logger.info(f"🎯 {len(df_final)} guías únicas encontradas en el archivo")
                
                # Aplicar filtrado y limpieza normal
                df_final = self._clean_and_filter_data(df_final)
                
                # Mostrar preview de las guías que se procesarán
                if len(df_final) > 0:
                    preview_guias = df_final['numero_guia'].head(10).tolist()
                    logger.info(f"📝 Primeras guías a procesar: {', '.join(preview_guias)}")
                
                return df_final
            else:
                logger.error("❌ No se encontraron guías válidas en ninguna columna del archivo")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ Error leyendo Excel: {str(e)}")
            return pd.DataFrame()
    
    def _buscar_guias_en_todas_las_columnas(self, df):
        """Buscar guías de 11 dígitos en TODAS las columnas del Excel"""
        import re
        
        todas_las_guias = []
        patron_guia = r'\b\d{11}\b'  # Patrón exacto para guías de 11 dígitos
        
        # Contadores para estadísticas
        stats = {
            'celdas_procesadas': 0,
            'celdas_con_guias': 0,
            'columnas_con_guias': set(),
            'guias_duplicadas': 0
        }
        
        logger.info("🔍 Búsqueda exhaustiva en todas las columnas...")
        
        for columna in df.columns:
            logger.info(f"   📑 Escaneando columna: '{columna}'")
            guias_en_esta_columna = 0
            
            for valor in df[columna]:
                if self._es_valor_valido(valor):
                    stats['celdas_procesadas'] += 1
                    valor_str = str(valor).strip()
                    
                    # Buscar guías usando regex
                    guias_encontradas = re.findall(patron_guia, valor_str)
                    
                    for guia in guias_encontradas:
                        if guia not in todas_las_guias:
                            todas_las_guias.append(guia)
                            guias_en_esta_columna += 1
                            stats['celdas_con_guias'] += 1
                            stats['columnas_con_guias'].add(columna)
                        else:
                            stats['guias_duplicadas'] += 1
            
            if guias_en_esta_columna > 0:
                logger.info(f"      ✅ Encontradas {guias_en_esta_columna} guías en esta columna")
        
        # Log detallado del proceso
        self._log_estadisticas_busqueda(stats, len(todas_las_guias))
        
        return todas_las_guias
    
    def _es_valor_valido(self, valor):
        """Verificar si el valor de celda puede contener una guía"""
        if pd.isna(valor) or valor is None:
            return False
        
        valor_str = str(valor).strip()
        valores_invalidos = ['', ' ', 'nan', 'NaN', 'None', 'null', 'NULL']
        
        return valor_str not in valores_invalidos
    
    def _log_estadisticas_busqueda(self, stats, total_guias):
        """Mostrar estadísticas detalladas de la búsqueda"""
        logger.info("📊 ESTADÍSTICAS DETALLADAS:")
        logger.info(f"   • Celdas totales procesadas: {stats['celdas_procesadas']}")
        logger.info(f"   • Celdas que contenían guías: {stats['celdas_con_guias']}")
        logger.info(f"   • Columnas con guías encontradas: {len(stats['columnas_con_guias'])}")
        logger.info(f"   • Guías únicas encontradas: {total_guias}")
        logger.info(f"   • Guías duplicadas ignoradas: {stats['guias_duplicadas']}")
        
        if stats['columnas_con_guias']:
            logger.info("   • Columnas donde se encontraron guías:")
            for columna in stats['columnas_con_guias']:
                logger.info(f"        - {columna}")
    
    def _clean_and_filter_data(self, df):
        """Limpiar y filtrar datos - CON MEJORES LOGS"""
        try:
            original_count = len(df)
            
            # Primero eliminar None values
            df = df[df['numero_guia'].notna()]
            
            # Convertir a string y limpiar
            df['numero_guia'] = df['numero_guia'].astype(str)
            
            # Filtrar filas inválidas
            df = df[
                (~df['numero_guia'].isna()) &
                (df['numero_guia'].str.strip() != '') &
                (df['numero_guia'].str.lower() != 'nan') &
                (df['numero_guia'] != 'None') &
                (df['numero_guia'] != 'null') &
                (~df['numero_guia'].str.contains(r'^\s*nan\s*$', case=False, na=False))
            ]
            
            # Remover .0 de los números flotantes
            df['numero_guia'] = df['numero_guia'].str.replace(r'\.0$', '', regex=True)
            
            # Limpiar espacios
            df['numero_guia'] = df['numero_guia'].str.strip()
            
            # ✅ FILTRADO POR LONGITUD DE GUÍA - SOLO 11 DÍGITOS
            df = self._filter_by_guide_length(df)
            
            # Log de limpieza
            removed_count = original_count - len(df)
            if removed_count > 0:
                logger.info(f"📊 Limpieza completada: {removed_count} guías eliminadas, {len(df)} guías válidas restantes")
            
            return df
                
        except Exception as e:
            logger.error(f"❌ Error en limpieza de datos: {str(e)}")
            return df

    def _filter_by_guide_length(self, df):
        """Filtrar guías por longitud - SOLO 11 DÍGITOS"""
        try:
            original_count = len(df)
            
            # Patrón para identificar guías de 11 dígitos
            eleven_digit_pattern = r'^\d{11}$'
            
            # Clasificar guías
            valid_guias = df['numero_guia'].str.match(eleven_digit_pattern, na=False)
            
            # Contar por tipo
            count_valid = valid_guias.sum()
            count_invalid = (~valid_guias).sum()
            
            # Log informativo
            logger.info("📋 CLASIFICACIÓN DE GUÍAS DETECTADA:")
            logger.info(f"   🟢 Válidas (11 dígitos): {count_valid} guías")
            logger.info(f"   ⚫ Inválidas: {count_invalid} guías (otros formatos)")
            
            # Mostrar ejemplos de cada tipo
            if count_valid > 0:
                ejemplos = df[valid_guias]['numero_guia'].head(3).tolist()
                logger.info(f"   📝 Ejemplos válidos: {', '.join(ejemplos)}")
            
            if count_invalid > 0:
                ejemplos = df[~valid_guias]['numero_guia'].head(3).tolist()
                logger.info(f"   📝 Ejemplos inválidos: {', '.join(ejemplos)}")
                logger.warning("   ⚠️  Las guías que no tienen 11 dígitos no se procesarán")
            
            # ✅ FILTRO CRÍTICO: Mantener SOLO guías de 11 dígitos
            df_filtrado = df[valid_guias].copy()
            
            removed_by_type = original_count - len(df_filtrado)
            if removed_by_type > 0:
                logger.warning(f"🚫 Se filtraron {removed_by_type} guías que NO tienen 11 dígitos")
                logger.info(f"✅ Se procesarán SOLO {len(df_filtrado)} guías válidas (11 dígitos)")
            
            return df_filtrado
            
        except Exception as e:
            logger.error(f"❌ Error en filtrado por longitud: {str(e)}")
            return df