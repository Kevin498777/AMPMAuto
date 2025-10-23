# main.py - Interfaz gráfica principal de AMPMAuto
import sys
import os
import pandas as pd
from datetime import datetime
import logging
import traceback

# Importar PyQt5 PRIMERO, antes de cualquier otro código
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                                 QPushButton, QLabel, QTextEdit, QProgressBar, 
                                 QFileDialog, QMessageBox, QWidget, QFrame, 
                                 QGroupBox, QTabWidget, QCheckBox)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont
    PYQT5_AVAILABLE = True
except ImportError as e:
    print(f"Error: PyQt5 no está instalado. Instala con: pip install PyQt5")
    print(f"Error detallado: {e}")
    PYQT5_AVAILABLE = False

# Solo importar nuestros módulos si PyQt5 está disponible
if PYQT5_AVAILABLE:
    # Importar módulos personalizados
    try:
        from automator import AMPMAutomatorRobusto as AMPMAutomator
    except ImportError:
        try:
            from automator import AMPMAutomatorRobusto as AMPMAutomator
        except ImportError:
            from automator import AMPMAutomator

    # Importar utils
    try:
        from utils.config import ConfigManager
        from utils.logger import setup_logger
    except ImportError:
        # Crear clases básicas si no existen los módulos
        class ConfigManager:
            def __init__(self):
                self.ampm_username = os.getenv('AMPM_USERNAME', '')
                self.ampm_password = os.getenv('AMPM_PASSWORD', '')
                self.timeout = 30
        
        def setup_logger():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
            return logging.getLogger(__name__)

    # Configurar logging
    logger = setup_logger()

    class DataHandler:
        """Manejador de datos para archivos Excel - VERSIÓN MEJORADA"""
        
        def __init__(self, excel_file_path):
            self.excel_file_path = excel_file_path
        
        def read_excel(self):
            """Leer archivo Excel y extraer guías - CON SOPORTE PARA JSON"""
            try:
                df = pd.read_excel(self.excel_file_path)
                
                # Verificar que tenga la columna necesaria
                if 'numero_guia' not in df.columns:
                    # Intentar mapear otras columnas comunes
                    column_mapping = {
                        'guia': 'numero_guia',
                        'número_guia': 'numero_guia', 
                        'guía': 'numero_guia',
                        'tracking': 'numero_guia',
                        'número': 'numero_guia',
                        'guia_number': 'numero_guia',
                        'guia_id': 'numero_guia'
                    }
                    
                    for old_col, new_col in column_mapping.items():
                        if old_col in df.columns:
                            df = df.rename(columns={old_col: new_col})
                            logger.info(f"✅ Columna renombrada: '{old_col}' -> 'numero_guia'")
                            break
                    else:
                        # Si no encuentra ninguna columna conocida, usar la primera
                        first_col = df.columns[0]
                        df = df.rename(columns={first_col: 'numero_guia'})
                        logger.info(f"✅ Usando primera columna: '{first_col}' -> 'numero_guia'")
                
                # ✅ NUEVO: PROCESAR GUÍAS EN FORMATO JSON
                df = self._process_json_guides(df)
                
                # ✅ FILTRADO NORMAL
                df = self._clean_and_filter_data(df)
                
                logger.info(f"📊 Archivo contiene {len(df)} guías válidas después de limpieza")
                
                if len(df) > 0:
                    sample_guias = df['numero_guia'].head(5).tolist()
                    logger.info(f"📋 Primeras guías válidas: {', '.join(map(str, sample_guias))}")
                else:
                    logger.warning("⚠️ No hay guías válidas después de la limpieza")
                
                return df
                    
            except Exception as e:
                logger.error(f"❌ Error leyendo Excel: {str(e)}")
                return pd.DataFrame()   
        
        def _clean_and_filter_data(self, df):
            """Limpiar y filtrar datos - CON MEJORES LOGS"""
            try:
                original_count = len(df)
                
                # Primero eliminar None values (de la extracción JSON)
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
                
                # ✅ FILTRADO POR TIPO DE GUÍA - SOLO MERCADO LIBRE
                df = self._filter_by_shipping_type(df)
                
                # Log de limpieza
                removed_count = original_count - len(df)
                if removed_count > 0:
                    logger.info(f"📊 Limpieza completada: {removed_count} guías eliminadas, {len(df)} guías válidas restantes")
                
                return df
                    
            except Exception as e:
                logger.error(f"❌ Error en limpieza de datos: {str(e)}")
                return df

        def _process_json_guides(self, df):
            """Procesar guías en formato JSON y extraer el número de guía"""
            try:
                import json
                import re
                
                original_count = len(df)
                processed_count = 0
                
                # Función para extraer guía de diferentes formatos
                def extract_guide_number(guide_value):
                    if pd.isna(guide_value) or guide_value is None:
                        return None
                        
                    guide_str = str(guide_value).strip()
                    
                    # Caso 1: Formato JSON como {"ID":"45706599155","t":"lm"}
                    if guide_str.startswith('{') and guide_str.endswith('}'):
                        try:
                            json_data = json.loads(guide_str)
                            if 'ID' in json_data:
                                extracted_guide = str(json_data['ID']).strip()
                                logger.info(f"✅ Extraída guía JSON: {guide_str} -> {extracted_guide}")
                                return extracted_guide
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ No se pudo decodificar JSON: {guide_str}")
                    
                    # Caso 2: Buscar patrones de guía en texto
                    # Patrón para guías de Mercado Libre (45 + 9 dígitos)
                    mercado_libre_pattern = r'45\d{9}'
                    matches = re.findall(mercado_libre_pattern, guide_str)
                    if matches:
                        logger.info(f"✅ Extraída guía de texto: {guide_str} -> {matches[0]}")
                        return matches[0]
                    
                    # Caso 3: Si ya es un número de guía válido, mantenerlo
                    if re.match(r'^45\d{9}$', guide_str):
                        return guide_str
                    
                    # Si no coincide con ningún patrón, devolver None (será filtrado después)
                    logger.warning(f"⚠️ Formato no reconocido: {guide_str}")
                    return None
                
                # Aplicar la extracción a todas las guías
                df['numero_guia'] = df['numero_guia'].apply(extract_guide_number)
                
                # Contar cuántas se procesaron exitosamente
                processed_count = df['numero_guia'].notna().sum()
                
                logger.info(f"📊 Procesamiento JSON: {processed_count}/{original_count} guías extraídas exitosamente")
                
                return df
                
            except Exception as e:
                logger.error(f"❌ Error procesando guías JSON: {str(e)}")
                return df

        def _filter_by_shipping_type(self, df):
            """Filtrar guías por tipo de transportista - SOLO MERCADO LIBRE"""
            try:
                original_count = len(df)
                
                # Patrones para identificar tipos de guías
                mercado_libre_pattern = r'^45\d{9}$'  # Guías Mercado Libre: empiezan con 45, 11 dígitos
                shein_pattern = r'^\d{10,12}$'        # Guías Shein: 10-12 dígitos (pero no empiezan con 45)
                ampm_pattern = r'^AMPM'               # Guías AMPM: empiezan con AMPM
                
                # Clasificar guías
                mercado_libre_guias = df['numero_guia'].str.match(mercado_libre_pattern, na=False)
                shein_guias = ~mercado_libre_guias & df['numero_guia'].str.match(shein_pattern, na=False)
                ampm_guias = df['numero_guia'].str.match(ampm_pattern, na=False)
                otras_guias = ~(mercado_libre_guias | shein_guias | ampm_guias)
                
                # Contar por tipo
                count_mercado_libre = mercado_libre_guias.sum()
                count_shein = shein_guias.sum()
                count_ampm = ampm_guias.sum()
                count_otras = otras_guias.sum()
                
                # Log informativo
                logger.info("📋 CLASIFICACIÓN DE GUÍAS DETECTADA:")
                logger.info(f"   🟢 Mercado Libre: {count_mercado_libre} guías (45 + 9 dígitos)")
                logger.info(f"   🔵 Shein: {count_shein} guías (10-12 dígitos)")
                logger.info(f"   🟡 AMPM: {count_ampm} guías (prefijo AMPM)")
                logger.info(f"   ⚫ Otras: {count_otras} guías (otros formatos)")
                
                # Mostrar ejemplos de cada tipo
                if count_mercado_libre > 0:
                    ejemplos = df[mercado_libre_guias]['numero_guia'].head(3).tolist()
                    logger.info(f"   📝 Ejemplos Mercado Libre: {', '.join(ejemplos)}")
                
                if count_shein > 0:
                    ejemplos = df[shein_guias]['numero_guia'].head(3).tolist()
                    logger.info(f"   📝 Ejemplos Shein: {', '.join(ejemplos)}")
                    logger.warning("   ⚠️  Las guías Shein requieren nombre del receptor - NO PROCESABLES")
                
                if count_ampm > 0:
                    ejemplos = df[ampm_guias]['numero_guia'].head(3).tolist()
                    logger.info(f"   📝 Ejemplos AMPM: {', '.join(ejemplos)}")
                
                # ✅ FILTRO CRÍTICO: Mantener SOLO guías de Mercado Libre
                df_filtrado = df[mercado_libre_guias].copy()
                
                removed_by_type = original_count - len(df_filtrado)
                if removed_by_type > 0:
                    logger.warning(f"🚫 Se filtraron {removed_by_type} guías que NO son de Mercado Libre")
                    logger.info(f"✅ Se procesarán SOLO {len(df_filtrado)} guías de Mercado Libre")
                
                return df_filtrado
                
            except Exception as e:
                logger.error(f"❌ Error en filtrado por tipo: {str(e)}")
                return df

    class ReportGenerator:
        """Generador de reportes"""
        
        def __init__(self, results=None):
            self.results = results or []
        
        def generate_report(self):
            """Generar reporte de resultados - VERSIÓN CORREGIDA Y CON DEBUG"""
            print("🔍 [DEBUG] generate_report() iniciado")
            
            if not self.current_report_data:
                error_msg = "❌ No hay datos de reporte disponibles"
                print(f"🔍 [DEBUG] {error_msg}")
                QMessageBox.warning(self, "Advertencia", error_msg)
                return None
            
            try:
                print("🔍 [DEBUG] Creando ReportGenerator...")
                
                # ✅ USAR SIEMPRE LA MISMA UBICACIÓN
                reports_dir = "reports"
                os.makedirs(reports_dir, exist_ok=True)
                print(f"🔍 [DEBUG] Directorio de reportes: {os.path.abspath(reports_dir)}")
                
                # ✅ GENERACIÓN DIRECTA SIN DEPENDENCIAS EXTERNAS
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = os.path.join(reports_dir, f"reporte_ampm_{timestamp}.xlsx")
                
                print(f"🔍 [DEBUG] Intentando crear: {report_path}")
                print(f"🔍 [DEBUG] Datos disponibles: {self.current_report_data.keys()}")
                
                # VERIFICAR ESTRUCTURA DE DATOS
                if 'results' not in self.current_report_data:
                    error_msg = "❌ No hay resultados en los datos del reporte"
                    print(f"🔍 [DEBUG] {error_msg}")
                    QMessageBox.warning(self, "Error", error_msg)
                    return None
                
                # PREPARAR DATOS
                report_rows = []
                for result in self.current_report_data.get('results', []):
                    report_rows.append({
                        'Guia': result.get('guia_number', 'N/A'),
                        'Estado': 'EXITOSO' if result.get('success') else 'FALLIDO',
                        'Mensaje': result.get('message', result.get('error', 'N/A')),
                        'Tiempo_Procesamiento': f"{result.get('processing_time', 0):.2f}s" if result.get('processing_time') else 'N/A',
                        'Timestamp': result.get('timestamp', 'N/A'),
                        'Recuperable': 'Sí' if result.get('recoverable') else 'No',
                        'Tipo_Error': 'Ya Entregada' if result.get('recoverable') else 'Error Real' if not result.get('success') else 'Éxito'
                    })
                
                print(f"🔍 [DEBUG] {len(report_rows)} filas preparadas para el reporte")
                
                # CREAR DATAFRAME Y GUARDAR
                df = pd.DataFrame(report_rows)
                df.to_excel(report_path, index=False)
                
                # VERIFICAR QUE SE CREÓ
                if os.path.exists(report_path):
                    file_size = os.path.getsize(report_path)
                    print(f"🔍 [DEBUG] ✅ Reporte creado exitosamente: {report_path} ({file_size} bytes)")
                    self.add_log_message(f"📋 Reporte generado: {report_path}")
                    
                    # MOSTRAR UBICACIÓN ABSOLUTA
                    absolute_path = os.path.abspath(report_path)
                    self.add_log_message(f"📁 Ubicación: {absolute_path}")
                    
                    return report_path
                else:
                    error_msg = "❌ El archivo de reporte no se creó"
                    print(f"🔍 [DEBUG] {error_msg}")
                    QMessageBox.warning(self, "Error", error_msg)
                    return None
                    
            except Exception as e:
                error_msg = f"❌ Error crítico al generar reporte: {str(e)}"
                print(f"🔍 [DEBUG] {error_msg}")
                print(f"🔍 [DEBUG] Traceback: {traceback.format_exc()}")
                self.add_log_message(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                return None

    class AutomationThread(QThread):
        """Hilo para ejecutar la automatización sin bloquear la interfaz gráfica"""
        
        # Señales para comunicación con la interfaz principal
        progress_updated = pyqtSignal(int, str)
        log_message = pyqtSignal(str)
        finished_success = pyqtSignal(dict)
        finished_error = pyqtSignal(str)
        
        def __init__(self, excel_file_path, headless=True):
            super().__init__()
            self.excel_file_path = excel_file_path
            self.headless = headless
            self.is_running = True
            
        def run(self):
            try:
                self.log_message.emit("🔍 Iniciando proceso de automatización...")
                
                # 1. Leer y validar datos del Excel
                self.log_message.emit("📊 Leyendo archivo Excel...")
                data_handler = DataHandler(self.excel_file_path)
                guias_df = data_handler.read_excel()
                
                if guias_df.empty:
                    self.finished_error.emit("El archivo Excel está vacío o no contiene guías válidas de Mercado Libre")
                    return
                    
                total_guias = len(guias_df)
                self.log_message.emit(f"📦 Se encontraron {total_guias} guías VÁLIDAS de Mercado Libre para procesar")
                
                # Mostrar las guías que se van a procesar
                guias_list = guias_df['numero_guia'].head(10).tolist()
                if total_guias > 10:
                    self.log_message.emit(f"📋 Guías a procesar (primeras 10): {', '.join(map(str, guias_list))}...")
                else:
                    self.log_message.emit(f"📋 Guías a procesar: {', '.join(map(str, guias_list))}")
                
                # 2. Inicializar automator
                self.log_message.emit("🚀 Inicializando navegador...")
                automator = AMPMAutomator(headless=self.headless)
                
                # 3. Procesar cada guía
                success_count = 0
                error_count = 0
                recovered_count = 0
                results = []
                
                # ✅ SOLUCIÓN: Usar enumerate() para obtener índice secuencial correcto
                for current_index, (index, guia_data) in enumerate(guias_df.iterrows(), 1):
                    if not self.is_running:
                        break
                        
                    # ✅ CÁLCULO CORRECTO DEL PROGRESO
                    progress = int((current_index) / total_guias * 100)
                    guia_number = str(guia_data.get('numero_guia', 'N/A')).strip()
                    self.progress_updated.emit(progress, f"Procesando guía {current_index} de {total_guias}")
                    
                    try:
                        self.log_message.emit(f"📝 Procesando guía: {guia_number}")
                        
                        # Procesar la guía usando el automator robusto
                        result = automator.process_shipment_with_retry(guia_data)
                        
                        # CORRECCIÓN: Usar el número real de guía en los resultados
                        result['guia_number'] = guia_number
                        results.append(result)
                        
                        if result['success']:
                            success_count += 1
                            processing_time = result.get('processing_time', 0)
                            self.log_message.emit(f"✅ Guía {guia_number} procesada exitosamente")
                            self.log_message.emit(f"   ⏱️ Tiempo: {processing_time:.2f}s")
                        else:
                            if result.get('recoverable', False):
                                recovered_count += 1
                                self.log_message.emit(f"⚠️ GUÍA YA ENTREGADA: {guia_number} - {result.get('error', 'Error desconocido')}")
                            else:
                                error_count += 1
                                self.log_message.emit(f"❌ ERROR: {guia_number} - {result.get('error', 'Error desconocido')}")
                                
                    except Exception as e:
                        error_count += 1
                        error_msg = f"❌ Error crítico en guía {guia_number}: {str(e)}"
                        self.log_message.emit(error_msg)
                        results.append({
                            'success': False, 
                            'error': error_msg,
                            'guia_number': guia_number,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'recoverable': False
                        })
                    
                    # Pequeña pausa entre guías
                    if self.is_running:
                        self.sleep(1)
                
                # 4. Cerrar navegador
                automator.close()
                
                # 5. Preparar reporte final - CORREGIDO EL CONTEO
                if self.is_running:
                    self.log_message.emit("📋 Generando reporte final...")
                    
                    # VERIFICACIÓN: Contar éxitos reales desde los resultados
                    real_success_count = sum(1 for r in results if r.get('success') == True)
                    real_recovered_count = sum(1 for r in results if r.get('recoverable') == True and not r.get('success'))
                    real_error_count = sum(1 for r in results if not r.get('success') and not r.get('recoverable'))
                    
                    # Usar los conteos reales en lugar de los acumulados
                    final_success_count = real_success_count
                    final_recovered_count = real_recovered_count
                    final_error_count = real_error_count
                    
                    # Log de verificación
                    self.log_message.emit(f"🔍 VERIFICACIÓN: Éxitos={final_success_count}, Entregadas={final_recovered_count}, Errores={final_error_count}")
                    
                    report_data = {
                        'total': total_guias,
                        'success': final_success_count,
                        'errors': final_error_count + final_recovered_count,  # Total de no-éxitos
                        'recovered': final_recovered_count,
                        'results': results,
                        'timestamp': datetime.now(),
                        'excel_file': self.excel_file_path
                    }
                    
                    self.finished_success.emit(report_data)
                    
            except Exception as e:
                error_msg = f"Error en el hilo de automatización: {str(e)}\n{traceback.format_exc()}"
                logger.error(error_msg)
                self.finished_error.emit(f"Error en el proceso: {str(e)}")
        
        def sleep(self, seconds):
            """Sleep que respeta la señal de stop"""
            for _ in range(seconds * 10):
                if not self.is_running:
                    break
                QThread.msleep(100)
        
        def stop(self):
            """Detener la ejecución del hilo"""
            self.is_running = False
            self.log_message.emit("⏹️ Proceso detenido por el usuario")

    class MainWindow(QMainWindow):
        """Ventana principal de la aplicación AMPMAuto"""
        
        def __init__(self):
            super().__init__()
            self.excel_file_path = None
            self.automation_thread = None
            self.current_report_data = None
            self.config = ConfigManager()
            self.init_ui()
            self.apply_styles()
            
        def init_ui(self):
            """Inicializar la interfaz de usuario"""
            self.setWindowTitle("AMPMAuto - Sistema de Automatización de Guías")
            self.setMinimumSize(900, 700)
            
            # Widget central
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Layout principal
            main_layout = QVBoxLayout(central_widget)
            main_layout.setSpacing(10)
            main_layout.setContentsMargins(15, 15, 15, 15)
            
            # Header
            header = self.create_header()
            main_layout.addWidget(header)
            
            # Contenido principal con tabs
            tabs = QTabWidget()
            
            # Tab de automatización
            automation_tab = self.create_automation_tab()
            tabs.addTab(automation_tab, "🚀 Automatización")
            
            # Tab de configuración
            config_tab = self.create_config_tab()
            tabs.addTab(config_tab, "⚙️ Configuración")
            
            main_layout.addWidget(tabs)
            
            # Footer
            footer = self.create_footer()
            main_layout.addWidget(footer)
            
        def create_header(self):
            """Crear el encabezado de la aplicación"""
            header_frame = QFrame()
            header_frame.setFrameStyle(QFrame.StyledPanel)
            header_layout = QVBoxLayout(header_frame)
            
            # Título
            title = QLabel("AMPMAuto - Sistema de Automatización")
            title.setAlignment(Qt.AlignCenter)
            title_font = QFont()
            title_font.setPointSize(18)
            title_font.setBold(True)
            title.setFont(title_font)
            subtitle_font = QFont()
            subtitle_font.setPointSize(16)
            
            # Subtítulo
            subtitle = QLabel("Carga automática de guías de envío en Grupo AMPM")
            subtitle.setAlignment(Qt.AlignCenter)
            subtitle_font = QFont()
            subtitle_font.setPointSize(12)
            subtitle.setFont(subtitle_font)
            
            header_layout.addWidget(title)
            header_layout.addWidget(subtitle)
            
            return header_frame
        
        def create_automation_tab(self):
            """Crear la pestaña de automatización"""
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setSpacing(15)
            
            # Grupo de selección de archivo
            file_group = QGroupBox("1. Seleccionar Archivo Excel")
            file_layout = QVBoxLayout(file_group)
            
            file_selection_layout = QHBoxLayout()
            self.file_label = QLabel("No se ha seleccionado ningún archivo")
            self.file_label.setStyleSheet("color: #666; font-style: italic;")
            self.file_label.setWordWrap(True)
            
            self.select_file_btn = QPushButton("📁 Seleccionar Excel")
            self.select_file_btn.clicked.connect(self.select_excel_file)
            self.select_file_btn.setMinimumWidth(150)
            
            file_selection_layout.addWidget(self.file_label, 1)
            file_selection_layout.addWidget(self.select_file_btn)
            file_layout.addLayout(file_selection_layout)
            
            # Grupo de progreso
            progress_group = QGroupBox("2. Progreso de Ejecución")
            progress_layout = QVBoxLayout(progress_group)
            
            # Barra de progreso
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            
            # Etiqueta de estado
            self.status_label = QLabel("Listo para comenzar")
            self.status_label.setAlignment(Qt.AlignCenter)
            self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
            
            # Área de logs
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setMaximumHeight(250)
            self.log_text.setPlaceholderText("Los logs de ejecución aparecerán aquí...")
            self.log_text.setFont(QFont("Consolas", 16))
            
            
            progress_layout.addWidget(self.status_label)
            progress_layout.addWidget(self.progress_bar)
            progress_layout.addWidget(QLabel("Logs de ejecución:"))
            progress_layout.addWidget(self.log_text)
            
            # Grupo de controles - MODIFICADO
            controls_group = QGroupBox("3. Controles")
            controls_layout = QHBoxLayout(controls_group)
            
            self.start_btn = QPushButton("🚀 Iniciar Automatización")
            self.start_btn.clicked.connect(self.start_automation)
            self.start_btn.setEnabled(False)
            self.start_btn.setMinimumHeight(40)
            
            self.stop_btn = QPushButton("⏹️ Detener")
            self.stop_btn.clicked.connect(self.stop_automation)
            self.stop_btn.setEnabled(False)
            self.stop_btn.setMinimumHeight(40)
            
            self.generate_report_btn = QPushButton("📊 Generar Reporte")
            self.generate_report_btn.clicked.connect(self.generate_report)
            self.generate_report_btn.setEnabled(False)
            self.generate_report_btn.setMinimumHeight(40)
            
            # ✅ NUEVO BOTÓN: Abrir carpeta de reportes
            self.open_reports_btn = QPushButton("📁 Abrir Carpeta de Reportes")
            self.open_reports_btn.clicked.connect(self.open_reports_folder)
            self.open_reports_btn.setMinimumHeight(40)
            self.open_reports_btn.setEnabled(True)  # Siempre habilitado
            
            controls_layout.addWidget(self.start_btn)
            controls_layout.addWidget(self.stop_btn)
            controls_layout.addWidget(self.generate_report_btn)
            controls_layout.addWidget(self.open_reports_btn)  # ✅ Agregar nuevo botón
            
            # Agregar grupos al layout
            layout.addWidget(file_group)
            layout.addWidget(progress_group)
            layout.addWidget(controls_group)
            layout.addStretch()
            
            return tab
        
        def create_config_tab(self):
            """Crear la pestaña de configuración"""
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setSpacing(15)
            
            config_group = QGroupBox("Configuración de la Aplicación")
            config_layout = QVBoxLayout(config_group)
            
            # Opciones de ejecución
            config_layout.addWidget(QLabel("Opciones de ejecución:"))
            
            headless_layout = QHBoxLayout()
            self.headless_checkbox = QCheckBox("Modo Headless (navegador oculto)")
            self.headless_checkbox.setChecked(True)
            headless_layout.addWidget(self.headless_checkbox)
            headless_layout.addStretch()
            config_layout.addLayout(headless_layout)
            
            # Información del sistema
            info_label = QLabel(
                f"AMPMAuto v1.3.2\n"
                f"Desarrollado por: Kevin Brian Ibarra Pineda ISIC\n"
                f"Python: {sys.version.split()[0]}\n"
                f"Directorio de trabajo: {os.getcwd()}\n\n"
                f"Características:\n"
                f"• Manejo robusto de errores\n"
                f"• Detección automática de modales\n"
                f"• Reintentos inteligentes\n"
                f"• Reportes detallados\n"
                f"• Filtrado automático de guías inválidas\n"
                f"• Manejo mejorado de loading"
            )
            info_label.setStyleSheet("""
                background-color: #f8f9fa; 
                padding: 15px; 
                border-radius: 5px; 
                border: 1px solid #dee2e6;
                line-height: 1.4;
            """)
            info_label.setWordWrap(True)
            
            config_layout.addWidget(QLabel("Información del sistema:"))
            config_layout.addWidget(info_label)
            
            layout.addWidget(config_group)
            layout.addStretch()
            
            return tab
        
        def create_footer(self):
            """Crear el pie de página"""
            footer = QLabel("© 2024 AMPMAuto -  Desarrollado por Kevin Brian Ibarra Pineda ISIC")
            footer.setAlignment(Qt.AlignCenter)
            footer.setStyleSheet("color: #6c757d; padding: 10px; border-top: 1px solid #dee2e6; margin-top: 10px;")
            return footer
        
        def apply_styles(self):
            """Aplicar estilos a la interfaz"""
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f8f9fa;
                    font-family: Segoe UI, Arial, sans-serif;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #dc3545;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 15px;
                    background-color: white;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    color: #dc3545;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 12px;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
                QPushButton:disabled {
                    background-color: #6c757d;
                    color: #adb5bd;
                }
                QPushButton:pressed {
                    background-color: #bd2130;
                }
                QProgressBar {
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    text-align: center;
                    height: 25px;
                    font-weight: bold;
                }
                QProgressBar::chunk {
                    background-color: #28a745;
                    border-radius: 5px;
                }
                QTextEdit {
                    border: 1px solid #ced4da;
                    border-radius: 6px;
                    padding: 8px;
                    background-color: white;
                    font-family: Consolas, Monaco, monospace;
                    font-size: 11px;
                }
                QTabWidget::pane {
                    border: 1px solid #dee2e6;
                    border-radius: 6px;
                    background-color: white;
                }
                QTabBar::tab {
                    background-color: #e9ecef;
                    border: 1px solid #dee2e6;
                    border-bottom: none;
                    padding: 8px 16px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: white;
                    border-bottom: 1px solid white;
                    margin-bottom: -1px;
                }
                QTabBar::tab:hover {
                    background-color: #dae0e5;
                }
                QCheckBox {
                    spacing: 8px;
                    font-weight: normal;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                    border-radius: 3px;
                    border: 2px solid #6c757d;
                }
                QCheckBox::indicator:checked {
                    background-color: #dc3545;
                    border-color: #dc3545;
                }
            """)
        
        def select_excel_file(self):
            """Seleccionar archivo Excel"""
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Seleccionar archivo Excel", 
                "", 
                "Excel Files (*.xlsx *.xls);;All Files (*)"
            )
            
            if file_path:
                self.excel_file_path = file_path
                file_name = os.path.basename(file_path)
                self.file_label.setText(f"📁 {file_name}")
                self.start_btn.setEnabled(True)
                self.add_log_message(f"✅ Archivo seleccionado: {file_path}")
                
                # Mostrar preview del archivo
                try:
                    df = pd.read_excel(file_path)
                    original_count = len(df)
                    
                    # Aplicar limpieza para el preview
                    data_handler = DataHandler(file_path)
                    df_clean = data_handler.read_excel()
                    clean_count = len(df_clean)
                    
                    self.add_log_message(f"📊 Archivo original: {original_count} guías")
                    self.add_log_message(f"📊 Después de limpieza: {clean_count} guías válidas")
                    
                    if clean_count > 0:
                        # Mostrar las primeras 5 guías como preview
                        sample_guias = df_clean['numero_guia'].head(5).tolist()
                        self.add_log_message(f"📋 Primeras guías válidas: {', '.join(map(str, sample_guias))}")
                    
                    if original_count > clean_count:
                        removed = original_count - clean_count
                        self.add_log_message(f"⚠️ Se eliminarán {removed} guías inválidas/vacías automáticamente")
                        
                except Exception as e:
                    self.add_log_message(f"⚠️ No se pudo leer el archivo: {str(e)}")
        
        def start_automation(self):
            """Iniciar el proceso de automatización"""
            if not self.excel_file_path:
                QMessageBox.warning(self, "Advertencia", "Por favor selecciona un archivo Excel primero.")
                return
            
            # Verificar que el archivo existe
            if not os.path.exists(self.excel_file_path):
                QMessageBox.critical(self, "Error", "El archivo seleccionado no existe.")
                return
            
            # Deshabilitar botones durante la ejecución
            self.start_btn.setEnabled(False)
            self.select_file_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.generate_report_btn.setEnabled(False)
            
            # Mostrar elementos de progreso
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Iniciando automatización...")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            
            # Limpiar logs anteriores
            self.log_text.clear()
            
            # Crear y ejecutar hilo de automatización
            headless = self.headless_checkbox.isChecked()
            self.automation_thread = AutomationThread(self.excel_file_path, headless)
            
            # Conectar señales
            self.automation_thread.progress_updated.connect(self.update_progress)
            self.automation_thread.log_message.connect(self.add_log_message)
            self.automation_thread.finished_success.connect(self.automation_finished)
            self.automation_thread.finished_error.connect(self.automation_error)
            
            # Iniciar hilo
            self.automation_thread.start()
            
            self.add_log_message("🚀 Iniciando proceso de automatización...")
            self.add_log_message(f"📁 Archivo: {os.path.basename(self.excel_file_path)}")
            self.add_log_message(f"🌐 Modo: {'Headless' if headless else 'Visible'}")
            self.add_log_message("🛡️  Sistema mejorado con filtrado automático de guías inválidas")
            

        
        def stop_automation(self):
            """Detener el proceso de automatización"""
            if self.automation_thread and self.automation_thread.isRunning():
                reply = QMessageBox.question(
                    self, 
                    "Confirmar Detención", 
                    "¿Estás seguro de que quieres detener el proceso?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.automation_thread.stop()
                    self.add_log_message("⏹️ Solicitando detención del proceso...")
                    self.status_label.setText("Deteniendo...")
        
        def update_progress(self, value, message):
            """Actualizar barra de progreso y estado"""
            self.progress_bar.setValue(value)
            self.status_label.setText(message)
            
            # Cambiar color según progreso
            if value < 30:
                self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            elif value < 70:
                self.status_label.setStyleSheet("color: #fd7e14; font-weight: bold;")
            else:
                self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        
        def add_log_message(self, message):
            """Agregar mensaje al área de logs"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
            # Auto-scroll al final
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        def automation_finished(self, report_data):
            """Proceso finalizado exitosamente"""
            self.current_report_data = report_data
            
            self.add_log_message("✅" * 50)
            self.add_log_message("🎉 PROCESO COMPLETADO EXITOSAMENTE")
            self.add_log_message("✅" * 50)
            
            success_count = report_data['success']
            recovered_count = report_data.get('recovered', 0)
            total_count = report_data['total']
            real_errors = report_data['errors'] - recovered_count  # Errores reales
            
            self.add_log_message(f"📊 RESUMEN FINAL:")
            self.add_log_message(f"   📦 Total de guías: {total_count}")
            self.add_log_message(f"   ✅ Guías exitosas: {success_count}")
            self.add_log_message(f"   ⚠️ Guías ya entregadas: {recovered_count}")
            self.add_log_message(f"   ❌ Errores reales: {real_errors}")
            
            if total_count > 0:
                effectiveness = (success_count / total_count) * 100
                self.add_log_message(f"   📈 Efectividad: {effectiveness:.1f}%")
            
            # Mostrar guías exitosas específicamente
            if success_count > 0:
                successful_guias = [r['guia_number'] for r in report_data['results'] if r.get('success')]
                if len(successful_guias) <= 10:
                    self.add_log_message(f"   🎯 Guías exitosas: {', '.join(successful_guias)}")
                else:
                    self.add_log_message(f"   🎯 Guías exitosas: {len(successful_guias)} guías procesadas correctamente")
            
            self.status_label.setText("Proceso completado exitosamente")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            self.progress_bar.setValue(100)
            
            # Habilitar botones
            self.stop_btn.setEnabled(False)
            self.select_file_btn.setEnabled(True)
            self.generate_report_btn.setEnabled(True)
            
            # ✅ GENERAR REPORTE AUTOMÁTICAMENTE
            report_path = self.generate_report()
            
            if report_path:
                self.add_log_message(f"📋 Reporte guardado en: {report_path}")
            else:
                self.add_log_message("❌ No se pudo generar el reporte automáticamente")
            
            # Mostrar resumen
            QMessageBox.information(
                self, 
                "Proceso Completado", 
                f"✅ Automatización finalizada exitosamente!\n\n"
                f"📦 Total de guías procesadas: {total_count}\n"
                f"✅ Guías exitosas: {success_count}\n"  
                f"⚠️ Guías ya entregadas: {recovered_count}\n"
                f"❌ Errores reales: {real_errors}\n"
                f"📈 Efectividad: {effectiveness:.1f}%\n\n"
                f"El reporte detallado se ha guardado automáticamente."
            )
        
        def automation_error(self, error_message):
            """Error en el proceso de automatización"""
            self.add_log_message("❌" * 50)
            self.add_log_message("💥 ERROR EN EL PROCESO")
            self.add_log_message("❌" * 50)
            self.add_log_message(f"❌ {error_message}")
            
            self.status_label.setText("Error en el proceso")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            
            QMessageBox.critical(
                self, 
                "Error en la Automatización", 
                f"Ocurrió un error durante la ejecución:\n\n{error_message}\n\n"
                f"Por favor verifica:\n"
                f"• Tu conexión a internet\n"
                f"• Las credenciales de AMPM\n"
                f"• El formato del archivo Excel"
            )
            
            self.reset_ui()
        
        def reset_ui(self):
            """Restablecer la interfaz a su estado inicial"""
            self.stop_btn.setEnabled(False)
            self.select_file_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
        
        def generate_report(self):
            """Generar reporte de resultados - VERSIÓN CORREGIDA CON RUTA CORRECTA"""
            try:
                # ✅ USAR LA MISMA RUTA QUE LOS LOGS (AppData/Local/AMPMAuto/reports/)
                from utils.logger import get_app_data_path
                base_dir = get_app_data_path()
                reports_dir = os.path.join(base_dir, "reports")
                os.makedirs(reports_dir, exist_ok=True)
                
                print(f"🔍 [DEBUG] Ruta de reportes: {reports_dir}")
                
                if not self.current_report_data:
                    QMessageBox.warning(self, "Advertencia", "No hay datos de reporte disponibles.")
                    return None
                
                # Generar nombre de archivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = os.path.join(reports_dir, f"reporte_ampm_{timestamp}.xlsx")
                
                print(f"🔍 [DEBUG] Intentando crear reporte en: {report_path}")
                
                # Preparar datos
                report_rows = []
                for result in self.current_report_data.get('results', []):
                    report_rows.append({
                        'Guia': result.get('guia_number', 'N/A'),
                        'Estado': 'EXITOSO' if result.get('success') else 'FALLIDO',
                        'Mensaje': result.get('message', result.get('error', 'N/A')),
                        'Tiempo_Procesamiento': f"{result.get('processing_time', 0):.2f}s" if result.get('processing_time') else 'N/A',
                        'Timestamp': result.get('timestamp', 'N/A'),
                        'Recuperable': 'Sí' if result.get('recoverable') else 'No',
                        'Tipo_Error': 'Ya Entregada' if result.get('recoverable') else 'Error Real' if not result.get('success') else 'Éxito'
                    })
                
                # Crear DataFrame y guardar
                df = pd.DataFrame(report_rows)
                df.to_excel(report_path, index=False)
                
                print(f"🔍 [DEBUG] Reporte creado exitosamente: {report_path}")
                
                # Mostrar en logs de la interfaz
                self.add_log_message(f"📋 Reporte generado: {report_path}")
                
                return report_path
                    
            except Exception as e:
                error_msg = f"❌ Error generando reporte: {str(e)}"
                print(f"🔍 [DEBUG] {error_msg}")
                import traceback
                print(f"🔍 [DEBUG] Traceback: {traceback.format_exc()}")
                self.add_log_message(error_msg)
                return None
            
        def open_reports_folder(self):
            """Abrir la carpeta de reportes en el explorador de archivos"""
            try:
                from utils.logger import get_app_data_path
                
                # Obtener la ruta de reportes (la misma que usamos para generar reportes)
                base_dir = get_app_data_path()
                reports_dir = os.path.join(base_dir, "reports")
                
                # Crear la carpeta si no existe
                os.makedirs(reports_dir, exist_ok=True)
                
                # Verificar si la carpeta existe
                if not os.path.exists(reports_dir):
                    QMessageBox.warning(self, "Advertencia", "La carpeta de reportes no existe.")
                    return
                
                # Abrir la carpeta en el explorador de archivos
                if os.name == 'nt':  # Windows
                    os.startfile(reports_dir)
                else:  # macOS y Linux
                    import subprocess
                    if sys.platform == "darwin":
                        subprocess.run(["open", reports_dir])
                    else:
                        subprocess.run(["xdg-open", reports_dir])
                
                self.add_log_message(f"📁 Carpeta de reportes abierta: {reports_dir}")
                
            except Exception as e:
                error_msg = f"❌ Error al abrir carpeta de reportes: {str(e)}"
                self.add_log_message(error_msg)
                QMessageBox.critical(self, "Error", error_msg)

def main():
    """Función principal de la aplicación"""
    if not PYQT5_AVAILABLE:
        print("ERROR: PyQt5 no está disponible.")
        print("Por favor instala PyQt5 con: pip install PyQt5")
        input("Presiona Enter para salir...")
        return 1
        
    try:
        # Verificar pandas
        try:
            import pandas as pd
        except ImportError:
            print("ERROR: pandas no está instalado.")
            print("Por favor instala pandas con: pip install pandas openpyxl")
            input("Presiona Enter para salir...")
            return 1

        # Crear aplicación
        app = QApplication(sys.argv)
        app.setApplicationName("AMPMAuto")
        app.setApplicationVersion("1.0")
        app.setApplicationDisplayName("AMPMAuto - Automatización de Guías")
        app.setFont(QFont("Segoe UI", 14))
        
        # Crear y mostrar ventana principal
        window = MainWindow()
        window.show()
        
        # Ejecutar aplicación
        return app.exec_()
        
    except Exception as e:
        error_msg = f"Error en la aplicación: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        QMessageBox.critical(
            None, 
            "Error Crítico", 
            f"La aplicación no pudo iniciarse:\n\n{str(e)}\n\n"
            f"Por favor contacta al administrador del sistema."
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())