import sys
import os
import pandas as pd
from datetime import datetime
import logging
import traceback
import json
import re


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
    # Importar módulos personalizados con manejo robusto de errores
    try:
        from automator import AMPMAutomatorRobusto as AMPMAutomator
        AUTOMATOR_AVAILABLE = True
    except ImportError as e:
        print(f"Advertencia: No se pudo importar AMPMAutomatorRobusto: {e}")
        try:
            from automator import AMPMAutomator
            AUTOMATOR_AVAILABLE = True
        except ImportError as e:
            print(f"Error: No se pudo importar ningún automator: {e}")
            AUTOMATOR_AVAILABLE = False

    # Importar utils con manejo de errores
    try:
        from utils.config import ConfigManager
        from utils.logger import setup_logger
        UTILS_AVAILABLE = True
    except ImportError as e:
        print(f"Advertencia: No se pudieron importar utils: {e}")
        # Crear clases básicas si no existen los módulos
        class ConfigManager:
            def __init__(self):
                self.ampm_username = os.getenv('AMPM_USERNAME', '')
                self.ampm_password = os.getenv('AMPM_PASSWORD', '')
                self.timeout = 30
        
        def setup_logger():
            logging.basicConfig(level=logging.INFO, 
                              format='%(asctime)s - %(levelname)s - %(message)s')
            return logging.getLogger(__name__)
        UTILS_AVAILABLE = False

    # Importar el ReportGenerator mejorado
    try:
        from report_generator import ReportGenerator, generate_detailed_report
        REPORT_GENERATOR_AVAILABLE = True
        print("✅ ReportGenerator disponible")
    except ImportError as e:
        print(f"Advertencia: No se pudo importar ReportGenerator: {e}")
        REPORT_GENERATOR_AVAILABLE = False

    # Configurar logging
    logger = setup_logger() if UTILS_AVAILABLE else logging.getLogger(__name__)

    class DataHandler:
        """Manejador de datos para archivos Excel - VERSIÓN MEJORADA"""
        
        def __init__(self, excel_file_path):
            self.excel_file_path = excel_file_path
        
        def read_excel(self):
            """Leer archivo Excel y extraer guías - CON SOPORTE PARA JSON"""
            try:
                # Verificar que el archivo existe
                if not os.path.exists(self.excel_file_path):
                    logger.error(f"❌ El archivo no existe: {self.excel_file_path}")
                    return pd.DataFrame()
                
                # Leer archivo Excel
                df = pd.read_excel(self.excel_file_path)
                logger.info(f"📊 Archivo Excel leído: {len(df)} filas encontradas")
                
                # Verificar que tenga datos
                if df.empty:
                    logger.warning("⚠️ El archivo Excel está vacío")
                    return df
                
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
                        'guia_id': 'numero_guia',
                        'tracking_number': 'numero_guia'
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
                
                # ✅ PROCESAR GUÍAS EN FORMATO JSON
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
                logger.error(traceback.format_exc())
                return pd.DataFrame()   

        def _clean_and_filter_data(self, df):
            """Limpiar y filtrar datos - CON MEJORES LOGS"""
            try:
                if df.empty:
                    return df
                    
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

        def _process_json_guides(self, df):
            """Procesar guías en formato JSON y extraer el número de guía"""
            try:
                if df.empty:
                    return df
                    
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
                    # Patrón para guías de 11 dígitos
                    eleven_digit_pattern = r'\b\d{11}\b'
                    matches = re.findall(eleven_digit_pattern, guide_str)
                    if matches:
                        logger.info(f"✅ Extraída guía de texto: {guide_str} -> {matches[0]}")
                        return matches[0]
                    
                    # Caso 3: Si ya es un número de guía válido, mantenerlo
                    if re.match(r'^\d{11}$', guide_str):
                        return guide_str
                    
                    # Si no coincide con ningún patrón, devolver el valor original
                    return guide_str
                
                # Aplicar la extracción a todas las guías
                df['numero_guia'] = df['numero_guia'].apply(extract_guide_number)
                
                # Contar cuántas se procesaron exitosamente
                processed_count = df['numero_guia'].notna().sum()
                
                logger.info(f"📊 Procesamiento JSON: {processed_count}/{original_count} guías procesadas")
                
                return df
                
            except Exception as e:
                logger.error(f"❌ Error procesando guías JSON: {str(e)}")
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

    class AutomationThread(QThread):
        """Hilo para ejecutar la automatización sin bloquear la interfaz gráfica - VERSIÓN OPTIMIZADA"""
        
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
                self.log_message.emit("🔍 Iniciando proceso de automatización RÁPIDO...")
                
                # Verificar disponibilidad del automator
                if not AUTOMATOR_AVAILABLE:
                    self.finished_error.emit("El módulo de automatización no está disponible. Verifica la instalación.")
                    return
                
                # 1. Leer y validar datos del Excel
                self.log_message.emit("📊 Leyendo archivo Excel...")
                data_handler = DataHandler(self.excel_file_path)
                guias_df = data_handler.read_excel()
                
                if guias_df.empty:
                    self.finished_error.emit("El archivo Excel está vacío o no contiene guías válidas de 11 dígitos")
                    return
                    
                total_guias = len(guias_df)
                self.log_message.emit(f"📦 Se encontraron {total_guias} guías VÁLIDAS (11 dígitos) para procesar")
                
                # Mostrar las guías que se van a procesar
                guias_list = guias_df['numero_guia'].head(10).tolist()
                if total_guias > 10:
                    self.log_message.emit(f"📋 Guías a procesar (primeras 10): {', '.join(map(str, guias_list))}...")
                else:
                    self.log_message.emit(f"📋 Guías a procesar: {', '.join(map(str, guias_list))}")
                
                # 2. Inicializar automator
                self.log_message.emit("🚀 Inicializando navegador...")
                automator = AMPMAutomator(headless=self.headless)
                
                # 3. Procesar cada guía CON MÁXIMA VELOCIDAD
                success_count = 0
                error_count = 0
                recovered_count = 0
                results = []
                
                for current_index, (index, guia_data) in enumerate(guias_df.iterrows(), 1):
                    if not self.is_running:
                        break
                        
                    # Cálculo del progreso
                    progress = int((current_index) / total_guias * 100)
                    guia_number = str(guia_data.get('numero_guia', 'N/A')).strip()
                    self.progress_updated.emit(progress, f"Procesando guía {current_index} de {total_guias}")
                    
                    try:
                        self.log_message.emit(f"📝 Procesando guía: {guia_number}")
                        
                        # Procesar la guía usando el automator optimizado
                        result = automator.process_shipment_with_retry(guia_data)
                        
                        # Usar el número real de guía en los resultados
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
                    
                    # ✅ PAUSA MÍNIMA entre guías para máxima velocidad (reducido de 1 a 0.2 segundos)
                    if self.is_running:
                        self.sleep(0.2)
                
                # 4. Cerrar navegador
                automator.close()
                
                # 5. Preparar reporte final
                if self.is_running:
                    self.log_message.emit("📋 Generando reporte final...")
                    
                    # Contar resultados reales
                    real_success_count = sum(1 for r in results if r.get('success') == True)
                    real_recovered_count = sum(1 for r in results if r.get('recoverable') == True and not r.get('success'))
                    real_error_count = sum(1 for r in results if not r.get('success') and not r.get('recoverable'))
                    
                    # Log de verificación
                    self.log_message.emit(f"🔍 VERIFICACIÓN: Éxitos={real_success_count}, Entregadas={real_recovered_count}, Errores={real_error_count}")
                    
                    report_data = {
                        'total': total_guias,
                        'success': real_success_count,
                        'errors': real_error_count + real_recovered_count,
                        'recovered': real_recovered_count,
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
            """Sleep optimizado que respeta la señal de stop - VERSIÓN MÁS RÁPIDA"""
            for _ in range(int(seconds * 20)):  # Más granular para mejor respuesta
                if not self.is_running:
                    break
                QThread.msleep(50)  # Reducido de 100 a 50 ms para mejor respuesta
        
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
            self.log_text.setMaximumHeight(350)
            self.log_text.setPlaceholderText("Los logs de ejecución aparecerán aquí...")
            self.log_text.setStyleSheet("""
    QTextEdit {
        background-color: #f8f9fa;           /* ← Gris muy claro casi blanco */
        color: #212529;                      /* ← Texto oscuro para contraste */
        border: 2px solid #ced4da;           /* ← Borde gris suave */
        border-radius: 8px;
        padding: 15px;
        font-family: Consolas, monospace;
        font-size: 14pt;                     /* ← Tamaño mantenido */
        font-weight: 500;
        line-height: 1.4;
        selection-background-color: #007bff; /* ← Azul para texto seleccionado */
        selection-color: white;
    }
""")
            
            
            progress_layout.addWidget(self.status_label)
            progress_layout.addWidget(self.progress_bar)
            progress_layout.addWidget(QLabel("Logs de ejecución:"))
            progress_layout.addWidget(self.log_text)
            
            # Grupo de controles
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
            
            self.generate_report_btn = QPushButton("📊 Generar Reporte Excel")
            self.generate_report_btn.clicked.connect(self.generate_report)
            self.generate_report_btn.setEnabled(False)
            self.generate_report_btn.setMinimumHeight(40)
            
            self.open_reports_btn = QPushButton("📁 Abrir Carpeta de Reportes")
            self.open_reports_btn.clicked.connect(self.open_reports_folder)
            self.open_reports_btn.setMinimumHeight(40)
            self.open_reports_btn.setEnabled(True)
            
            controls_layout.addWidget(self.start_btn)
            controls_layout.addWidget(self.stop_btn)
            controls_layout.addWidget(self.generate_report_btn)
            controls_layout.addWidget(self.open_reports_btn)
            
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
            system_info = f"""
AMPMAuto v1.4.0 - VERSIÓN RÁPIDA
Desarrollado por: Kevin Brian Ibarra Pineda ISIC
Python: {sys.version.split()[0]}
Directorio de trabajo: {os.getcwd()}

Módulos disponibles:
• PyQt5: {'✅' if PYQT5_AVAILABLE else '❌'}
• Automator: {'✅' if AUTOMATOR_AVAILABLE else '❌'}
• ReportGenerator: {'✅' if REPORT_GENERATOR_AVAILABLE else '❌'}
• Utils: {'✅' if UTILS_AVAILABLE else '❌'}

Características:
• Manejo robusto de errores
• Detección automática de modales  
• Reintentos inteligentes
• Reportes Excel detallados
• Filtrado automático de guías inválidas
• Manejo mejorado de loading
• Generación automática de reportes Excel
• OPTIMIZADO PARA VELOCIDAD: 10-15 guías/minuto
"""
            info_label = QLabel(system_info)
            info_label.setStyleSheet("""
                background-color: #f8f9fa; 
                padding: 15px; 
                border-radius: 5px; 
                border: 1px solid #dee2e6;
                line-height: 1.4;
                font-family: Consolas, monospace;
                font-size: 10px;
            """)
            info_label.setWordWrap(True)
            
            config_layout.addWidget(QLabel("Información del sistema:"))
            config_layout.addWidget(info_label)
            
            layout.addWidget(config_group)
            layout.addStretch()
            
            return tab
        
        def create_footer(self):
            """Crear el pie de página"""
            footer = QLabel("© 2024 AMPMAuto - Desarrollado por Kevin Brian Ibarra Pineda ISIC")
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
                    self.add_log_message(f"📊 Después de limpieza: {clean_count} guías válidas (11 dígitos)")
                    
                    if clean_count > 0:
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
            
            if not os.path.exists(self.excel_file_path):
                QMessageBox.critical(self, "Error", "El archivo seleccionado no existe.")
                return
            
            if not AUTOMATOR_AVAILABLE:
                QMessageBox.critical(self, "Error", 
                    "El módulo de automatización no está disponible.\n\n"
                    "Verifica que:\n"
                    "• Selenium esté instalado: pip install selenium\n"
                    "• El archivo automator.py exista\n"
                    "• Los drivers del navegador estén configurados")
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
            
            self.add_log_message("🚀 Iniciando proceso de automatización RÁPIDO...")
            self.add_log_message(f"📁 Archivo: {os.path.basename(self.excel_file_path)}")
            self.add_log_message(f"🌐 Modo: {'Headless' if headless else 'Visible'}")
            self.add_log_message("⚡ SISTEMA OPTIMIZADO PARA ALTA VELOCIDAD: 10-15 guías/minuto")
            self.add_log_message("🛡️  Sistema mejorado con filtrado automático de guías inválidas (solo 11 dígitos)")
        
        def stop_automation(self):
            """Detener el proceso de automatización - VERSIÓN MEJORADA"""
            if self.automation_thread and self.automation_thread.isRunning():
                reply = QMessageBox.question(
                    self, 
                    "Confirmar Detención", 
                    "¿Estás seguro de que quieres detener el proceso?\n\nSe perderá el progreso actual.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Deshabilitar botón de detener inmediatamente para evitar múltiples clics
                    self.stop_btn.setEnabled(False)
                    self.add_log_message("⏹️ Solicitando detención del proceso...")
                    self.status_label.setText("Deteniendo...")
                    self.status_label.setStyleSheet("color: #fd7e14; font-weight: bold;")
                    
                    # Detener el hilo
                    self.automation_thread.stop()
                    
                    # ✅ CONEXIÓN TEMPORAL para resetear la UI cuando el hilo termine
                    self.automation_thread.finished.connect(self._on_automation_stopped)
            
        def _on_automation_stopped(self):
            """Manejador cuando el hilo se detiene"""
            try:
                self.add_log_message("🛑 PROCESO DETENIDO POR EL USUARIO")
                self.add_log_message("📊 Progreso actual perdido - puedes reiniciar con un nuevo archivo")
                
                # Resetear la UI
                self.reset_ui()
                
                # Actualizar estado
                self.status_label.setText("Proceso detenido por el usuario")
                self.status_label.setStyleSheet("color: #fd7e14; font-weight: bold;")
                self.progress_bar.setValue(0)
                
                # Desconectar la señal para evitar múltiples llamadas
                try:
                    self.automation_thread.finished.disconnect(self._on_automation_stopped)
                except:
                    pass
                    
            except Exception as e:
                self.add_log_message(f"⚠️ Error al detener proceso: {str(e)}")
                self.reset_ui()
        
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
            real_errors = report_data['errors'] - recovered_count
            
            self.add_log_message(f"📊 RESUMEN FINAL:")
            self.add_log_message(f"   📦 Total de guías: {total_count}")
            self.add_log_message(f"   ✅ Guías exitosas: {success_count}")
            self.add_log_message(f"   ⚠️ Guías ya entregadas: {recovered_count}")
            self.add_log_message(f"   ❌ Errores reales: {real_errors}")
            
            if total_count > 0:
                effectiveness = (success_count / total_count) * 100
                self.add_log_message(f"   📈 Efectividad: {effectiveness:.1f}%")
                
                # Calcular velocidad promedio
                total_time = sum(r.get('processing_time', 0) for r in report_data['results'] if r.get('processing_time'))
                if total_time > 0:
                    guias_por_minuto = (total_count / total_time) * 60
                    self.add_log_message(f"   ⚡ Velocidad promedio: {guias_por_minuto:.1f} guías/minuto")
            
            # Mostrar guías exitosas
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
            
            # ✅ GENERAR REPORTE AUTOMÁTICAMENTE SOLO EXCEL
            if REPORT_GENERATOR_AVAILABLE:
                self.add_log_message("📋 Generando reporte Excel...")
                excel_path = generate_detailed_report(
                    results=report_data['results'],
                    excel_file=os.path.basename(self.excel_file_path)
                )
                
                if excel_path:
                    self.add_log_message(f"📊 Reporte Excel generado: {excel_path}")
                else:
                    self.add_log_message("⚠️ No se pudo generar el reporte Excel automáticamente")
            else:
                self.add_log_message("⚠️ ReportGenerator no disponible - generando reporte básico")
                # Fallback al método anterior
                excel_path = self._generate_basic_report()
                if excel_path:
                    self.add_log_message(f"📋 Reporte básico generado: {excel_path}")
            
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
                f"El reporte Excel se ha guardado automáticamente."
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
                f"• El formato del archivo Excel\n"
                f"• Que Selenium esté instalado correctamente"
            )
            
            self.reset_ui()
        
        def reset_ui(self):
            """Restablecer la interfaz a su estado inicial - VERSIÓN MEJORADA"""
            try:
                # Habilitar/Deshabilitar botones correctamente
                self.stop_btn.setEnabled(False)
                self.select_file_btn.setEnabled(True)
                self.start_btn.setEnabled(True if self.excel_file_path else False)
                self.generate_report_btn.setEnabled(True if self.current_report_data else False)
                
                # Ocultar barra de progreso
                self.progress_bar.setVisible(False)
                self.progress_bar.setValue(0)
                
                # Forzar actualización de la interfaz
                QApplication.processEvents()
                
            except Exception as e:
                print(f"Error en reset_ui: {e}")
        
        def generate_report(self):
            """Generar reporte de resultados - VERSIÓN MEJORADA (SOLO EXCEL)"""
            if not self.current_report_data:
                QMessageBox.warning(self, "Advertencia", "No hay datos de reporte disponibles.")
                return None
            
            try:
                if REPORT_GENERATOR_AVAILABLE:
                    self.add_log_message("📋 Generando reporte Excel...")
                    excel_path = generate_detailed_report(
                        results=self.current_report_data.get('results', []),
                        excel_file=os.path.basename(self.excel_file_path) if self.excel_file_path else "N/A"
                    )
                    
                    if excel_path:
                        self.add_log_message(f"📊 Reporte Excel generado: {excel_path}")
                        return excel_path
                    else:
                        self.add_log_message("❌ No se pudo generar el reporte Excel")
                        return None
                else:
                    self.add_log_message("⚠️ ReportGenerator no disponible - usando generador básico")
                    return self._generate_basic_report()
                    
            except Exception as e:
                error_msg = f"❌ Error generando reporte: {str(e)}"
                self.add_log_message(error_msg)
                QMessageBox.critical(self, "Error", error_msg)
                return None
        
        def _generate_basic_report(self):
            """Generar reporte básico (fallback)"""
            try:
                # Crear carpeta de reportes si no existe
                reports_dir = "reports"
                os.makedirs(reports_dir, exist_ok=True)
                
                # Generar nombre de archivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_path = os.path.join(reports_dir, f"reporte_ampm_{timestamp}.xlsx")
                
                # Preparar datos básicos
                report_rows = []
                for result in self.current_report_data.get('results', []):
                    report_rows.append({
                        'Guia': result.get('guia_number', 'N/A'),
                        'Estado': 'EXITOSO' if result.get('success') else 'FALLIDO',
                        'Mensaje': result.get('message', result.get('error', 'N/A')),
                        'Tiempo_Procesamiento': f"{result.get('processing_time', 0):.2f}s" if result.get('processing_time') else 'N/A',
                        'Timestamp': result.get('timestamp', 'N/A'),
                        'Recuperable': 'Sí' if result.get('recoverable') else 'No'
                    })
                
                # Crear DataFrame y guardar
                df = pd.DataFrame(report_rows)
                df.to_excel(report_path, index=False)
                
                if os.path.exists(report_path):
                    self.add_log_message(f"📋 Reporte básico generado: {report_path}")
                    return report_path
                else:
                    self.add_log_message("❌ No se pudo crear el archivo de reporte")
                    return None
                    
            except Exception as e:
                error_msg = f"❌ Error en generador básico: {str(e)}"
                self.add_log_message(error_msg)
                return None
            
        def open_reports_folder(self):
            """Abrir la carpeta de reportes en el explorador de archivos"""
            try:
                if REPORT_GENERATOR_AVAILABLE:
                    from report_generator import get_app_data_path
                    reports_dir = os.path.join(get_app_data_path(), "reports")
                else:
                    reports_dir = "reports"
                
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
                
                self.add_log_message(f"📁 Carpeta de reportes abierta: {os.path.abspath(reports_dir)}")
                
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
        app.setApplicationVersion("1.6.0")
        app.setApplicationDisplayName("AMPMAuto - Automatización de Guías")
        app.setFont(QFont("Segoe UI", 10))
        
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