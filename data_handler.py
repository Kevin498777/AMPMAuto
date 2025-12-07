# data_handler.py
import pandas as pd
import logging
import re

logger = logging.getLogger(__name__)

# DataHandler mejorado - BUSCA GUÍAS EN TODAS LAS COLUMNAS
class DataHandler:
    """Manejador de datos para archivos Excel - VERSIÓN MEJORADA CON BÚSQUEDA EN TODAS LAS COLUMNAS"""
    
    def __init__(self, excel_file_path):
        self.excel_file_path = excel_file_path
    
    def read_excel(self):
        """Leer archivo Excel y extraer guías de TODAS las columnas - VERSIÓN ROBUSTA"""
        try:
            # ✅ CAMBIO CRÍTICO: Leer sin encabezados para no perder la primera fila
            df = pd.read_excel(self.excel_file_path, header=None)
            logger.info(f"📊 Archivo Excel cargado: {len(df)} filas, {len(df.columns)} columnas")
            logger.info(f"📋 Columnas detectadas (sin encabezado): Columnas 0-{len(df.columns)-1}")
            
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
        todas_las_guias = []
        patron_guia = r'\b\d{11}\b'  # Patrón exacto para guías de 11 dígitos
        
        # Contadores para estadísticas
        stats = {
            'celdas_procesadas': 0,
            'celdas_con_guias': 0,
            'columnas_con_guias': set(),
            'guias_duplicadas': 0,
            'guias_procesadas': []
        }
        
        logger.info("🔍 Búsqueda exhaustiva en todas las columnas...")
        
        # ✅ CORRECCIÓN: También buscar en la primera fila (que antes se perdía)
        # Procesar TODAS las filas, incluyendo la fila 0
        for idx, fila in df.iterrows():
            fila_numero = idx + 1  # +1 para mostrar número de fila humano (1-indexed)
            logger.info(f"   📑 Procesando fila {fila_numero} de {len(df)}...")
            guias_en_esta_fila = 0
            
            for columna, valor in fila.items():
                if self._es_valor_valido(valor):
                    stats['celdas_procesadas'] += 1
                    valor_str = str(valor).strip()
                    
                    # ✅ MEJORA: Buscar guías usando regex más robusto
                    # Buscar directamente números de 11 dígitos
                    if re.match(r'^\d{11}$', valor_str):
                        guias_encontradas = [valor_str]
                    else:
                        # Buscar en cualquier parte del texto
                        guias_encontradas = re.findall(patron_guia, valor_str)
                    
                    for guia in guias_encontradas:
                        # ✅ Asegurar que la guía tenga exactamente 11 dígitos
                        if len(guia) == 11 and guia.isdigit():
                            if guia not in todas_las_guias:
                                todas_las_guias.append(guia)
                                guias_en_esta_fila += 1
                                stats['celdas_con_guias'] += 1
                                stats['columnas_con_guias'].add(columna)
                                stats['guias_procesadas'].append({
                                    'fila': fila_numero,  # Usar número de fila humano
                                    'columna': columna,
                                    'valor_original': valor_str[:50] + '...' if len(valor_str) > 50 else valor_str,
                                    'guia': guia
                                })
                            else:
                                stats['guias_duplicadas'] += 1
            
            if guias_en_esta_fila > 0:
                logger.info(f"      ✅ Encontradas {guias_en_esta_fila} guías en esta fila")
        
        # ✅ LOG DETALLADO DE LO QUE SE ENCONTRÓ
        self._log_estadisticas_busqueda(stats, len(todas_las_guias))
        
        # ✅ MOSTRAR LAS PRIMERAS 10 GUÍAS ENCONTRADAS PARA VERIFICACIÓN
        if todas_las_guias:
            logger.info("🔍 VERIFICACIÓN DE GUÍAS ENCONTRADAS:")
            for i, guia in enumerate(todas_las_guias[:10], 1):
                logger.info(f"   {i}. {guia}")
            if len(todas_las_guias) > 10:
                logger.info(f"   ... y {len(todas_las_guias) - 10} más")
        
        return todas_las_guias
    
    def _es_valor_valido(self, valor):
        """Verificar si el valor de celda puede contener una guía - MEJORADO"""
        if pd.isna(valor) or valor is None:
            return False
        
        valor_str = str(valor).strip()
        
        # Lista de valores inválidos
        valores_invalidos = [
            '', ' ', 'nan', 'NaN', 'None', 'null', 'NULL',
            'nan', 'N/A', 'n/a', '#N/A', '#VALUE!', '#REF!',
            'undefined', 'Undefined'
        ]
        
        # Verificar si es un valor inválido
        if valor_str in valores_invalidos:
            return False
        
        # Verificar si parece ser un número (contiene dígitos)
        # Esto incluye números como 45123456789 o texto que contenga números
        if not any(char.isdigit() for char in valor_str):
            return False
        
        # ✅ ACEPTAR CUALQUIER VALOR QUE CONTENGA DÍGITOS
        # Incluso si tiene otros caracteres, lo procesaremos para extraer números
        return True
    
    def _log_estadisticas_busqueda(self, stats, total_guias):
        """Mostrar estadísticas detalladas de la búsqueda - MEJORADO"""
        logger.info("📊 ESTADÍSTICAS DETALLADAS:")
        logger.info(f"   • Celdas totales procesadas: {stats['celdas_procesadas']}")
        logger.info(f"   • Celdas que contenían guías: {stats['celdas_con_guias']}")
        logger.info(f"   • Columnas con guías encontradas: {len(stats['columnas_con_guias'])}")
        logger.info(f"   • Guías únicas encontradas: {total_guias}")
        logger.info(f"   • Guías duplicadas ignoradas: {stats['guias_duplicadas']}")
        
        if stats['columnas_con_guias']:
            logger.info("   • Columnas donde se encontraron guías:")
            for columna in stats['columnas_con_guias']:
                logger.info(f"        - Columna {columna}")
        
        # ✅ MOSTRAR DETALLES DE LAS PRIMERAS 3 GUÍAS PROCESADAS
        if stats['guias_procesadas']:
            logger.info("   • Ejemplos de guías encontradas:")
            for i, guia_info in enumerate(stats['guias_procesadas'][:3], 1):
                logger.info(f"        {i}. Fila {guia_info['fila']}, Columna {guia_info['columna']}:")
                logger.info(f"           Original: '{guia_info['valor_original']}'")
                logger.info(f"           Guía extraída: {guia_info['guia']}")
    
    def _clean_and_filter_data(self, df):
        """Limpiar y filtrar datos - CON MEJORES LOGS"""
        try:
            if df.empty:
                return df
            
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
            if df.empty:
                return df
            
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