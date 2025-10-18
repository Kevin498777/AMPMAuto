# main.py - Interfaz gráfica principal de AMPMAuto
import sys
import os
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QProgressBar, 
                             QFileDialog, QMessageBox, QWidget, QFrame, 
                             QGroupBox, QTabWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import logging

# Importar módulos personalizados
from automator import AMPMAutomator
from data_handler import DataHandler
from report_generator import ReportGenerator
from utils.config import ConfigManager
from utils.logger import setup_logger

# Configurar logging
logger = setup_logger()

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
                self.finished_error.emit("El archivo Excel está vacío o no contiene datos válidos")
                return
                
            self.log_message.emit(f"📦 Se encontraron {len(guias_df)} guías para procesar")
            
            # 2. Inicializar automator
            self.log_message.emit("🚀 Inicializando navegador...")
            automator = AMPMAutomator(headless=self.headless)
            
            # 3. Procesar cada guía
            success_count = 0
            error_count = 0
            results = []
            
            for index, guia in guias_df.iterrows():
                if not self.is_running:
                    break
                    
                progress = int((index + 1) / len(guias_df) * 100)
                self.progress_updated.emit(progress, f"Procesando guía {index + 1} de {len(guias_df)}")
                
                try:
                    self.log_message.emit(f"📝 Procesando guía: {guia.get('numero_guia', 'N/A')}")
                    
                    # Aquí irá la lógica de automatización
                    result = automator.process_shipment(guia)
                    results.append(result)
                    
                    if result['success']:
                        success_count += 1
                        self.log_message.emit(f"✅ Guía {guia.get('numero_guia', 'N/A')} procesada exitosamente")
                    else:
                        error_count += 1
                        self.log_message.emit(f"❌ Error en guía {guia.get('numero_guia', 'N/A')}: {result['error']}")
                        
                except Exception as e:
                    error_count += 1
                    self.log_message.emit(f"❌ Error crítico en guía: {str(e)}")
                    results.append({'success': False, 'error': str(e)})
            
            # 4. Cerrar navegador
            automator.close()
            
            # 5. Generar reporte
            if self.is_running:
                self.log_message.emit("📋 Generando reporte final...")
                report_data = {
                    'total': len(guias_df),
                    'success': success_count,
                    'errors': error_count,
                    'results': results,
                    'timestamp': datetime.now()
                }
                
                self.finished_success.emit(report_data)
                
        except Exception as e:
            logger.error(f"Error en el hilo de automatización: {str(e)}")
            self.finished_error.emit(f"Error en el proceso: {str(e)}")
    
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
        self.config = ConfigManager()
        self.init_ui()
        self.apply_styles()
        
    def init_ui(self):
        """Inicializar la interfaz de usuario"""
        self.setWindowTitle("AMPMAuto - Sistema de Automatización de Guías")
        self.setFixedSize(900, 700)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        
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
        
        # Grupo de selección de archivo
        file_group = QGroupBox("1. Seleccionar Archivo Excel")
        file_layout = QVBoxLayout(file_group)
        
        file_selection_layout = QHBoxLayout()
        self.file_label = QLabel("No se ha seleccionado ningún archivo")
        self.file_label.setStyleSheet("color: #666; font-style: italic;")
        
        self.select_file_btn = QPushButton("📁 Seleccionar Excel")
        self.select_file_btn.clicked.connect(self.select_excel_file)
        
        file_selection_layout.addWidget(self.file_label)
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
        
        # Área de logs
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        
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
        
        self.stop_btn = QPushButton("⏹️ Detener")
        self.stop_btn.clicked.connect(self.stop_automation)
        self.stop_btn.setEnabled(False)
        
        self.generate_report_btn = QPushButton("📊 Generar Reporte")
        self.generate_report_btn.clicked.connect(self.generate_report)
        self.generate_report_btn.setEnabled(False)
        
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.generate_report_btn)
        
        # Agregar grupos al layout
        layout.addWidget(file_group)
        layout.addWidget(progress_group)
        layout.addWidget(controls_group)
        
        return tab
    
    def create_config_tab(self):
        """Crear la pestaña de configuración"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        config_group = QGroupBox("Configuración de la Aplicación")
        config_layout = QVBoxLayout(config_group)
        
        # Opciones de ejecución
        self.headless_checkbox = QPushButton("🌐 Modo Headless: Activado")
        self.headless_checkbox.setCheckable(True)
        self.headless_checkbox.setChecked(True)
        self.headless_checkbox.clicked.connect(self.toggle_headless)
        
        # Información del sistema
        info_label = QLabel(
            f"AMPMAuto v1.0\n"
            f"Python: {sys.version.split()[0]}\n"
            f"Directorio de trabajo: {os.getcwd()}"
        )
        info_label.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 5px;")
        
        config_layout.addWidget(QLabel("Opciones de ejecución:"))
        config_layout.addWidget(self.headless_checkbox)
        config_layout.addWidget(QLabel("Información del sistema:"))
        config_layout.addWidget(info_label)
        
        layout.addWidget(config_group)
        layout.addStretch()
        
        return tab
    
    def create_footer(self):
        """Crear el pie de página"""
        footer = QLabel("© 2024 AMPMAuto - Sistema desarrollado para Grupo AMPM")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #888; padding: 10px; border-top: 1px solid #ddd;")
        return footer
    
    def apply_styles(self):
        """Aplicar estilos a la interfaz"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dc3545;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #dc3545;
            }
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            QPushButton:checked {
                background-color: #28a745;
            }
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                width: 20px;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
    
    def select_excel_file(self):
        """Seleccionar archivo Excel"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar archivo Excel", 
            "", 
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            self.excel_file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.start_btn.setEnabled(True)
            self.log_text.append(f"📁 Archivo seleccionado: {file_path}")
    
    def toggle_headless(self):
        """Alternar modo headless"""
        if self.headless_checkbox.isChecked():
            self.headless_checkbox.setText("🌐 Modo Headless: Activado")
        else:
            self.headless_checkbox.setText("🌐 Modo Headless: Desactivado")
    
    def start_automation(self):
        """Iniciar el proceso de automatización"""
        if not self.excel_file_path:
            QMessageBox.warning(self, "Advertencia", "Por favor selecciona un archivo Excel primero.")
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
    
    def stop_automation(self):
        """Detener el proceso de automatización"""
        if self.automation_thread and self.automation_thread.isRunning():
            self.automation_thread.stop()
            self.automation_thread.quit()
            self.automation_thread.wait()
            
            self.add_log_message("⏹️ Proceso detenido por el usuario")
            self.status_label.setText("Proceso detenido")
            self.reset_ui()
    
    def update_progress(self, value, message):
        """Actualizar barra de progreso y estado"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def add_log_message(self, message):
        """Agregar mensaje al área de logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Auto-scroll al final
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def automation_finished(self, report_data):
        """Proceso finalizado exitosamente"""
        self.add_log_message(f"✅ Proceso completado!")
        self.add_log_message(f"📊 Resultados: {report_data['success']} exitosas, {report_data['errors']} errores de {report_data['total']} totales")
        
        self.status_label.setText("Proceso completado exitosamente")
        self.progress_bar.setValue(100)
        
        # Generar reporte automáticamente
        self.generate_report_btn.setEnabled(True)
        self.generate_report_btn.click()  # Generar reporte automáticamente
        
        self.reset_ui()
        
        # Mostrar resumen
        QMessageBox.information(
            self, 
            "Proceso Completado", 
            f"✅ Automatización finalizada\n\n"
            f"📦 Total de guías: {report_data['total']}\n"
            f"✅ Exitosa: {report_data['success']}\n"
            f"❌ Errores: {report_data['errors']}\n\n"
            f"El reporte se ha guardado en la carpeta 'reports/'"
        )
    
    def automation_error(self, error_message):
        """Error en el proceso de automatización"""
        self.add_log_message(f"❌ Error: {error_message}")
        self.status_label.setText("Error en el proceso")
        
        QMessageBox.critical(self, "Error", f"Ocurrió un error durante la automatización:\n\n{error_message}")
        self.reset_ui()
    
    def reset_ui(self):
        """Restablecer la interfaz a su estado inicial"""
        self.stop_btn.setEnabled(False)
        self.select_file_btn.setEnabled(True)
        self.generate_report_btn.setEnabled(True)
    
    def generate_report(self):
        """Generar reporte de resultados"""
        try:
            # En una implementación real, aquí se generaría el reporte con los datos
            report_generator = ReportGenerator()
            report_path = report_generator.generate_report()
            
            self.add_log_message(f"📋 Reporte generado: {report_path}")
            QMessageBox.information(self, "Reporte Generado", f"El reporte se ha guardado en:\n{report_path}")
            
        except Exception as e:
            self.add_log_message(f"❌ Error al generar reporte: {str(e)}")
            QMessageBox.warning(self, "Error", f"No se pudo generar el reporte:\n{str(e)}")

def main():
    """Función principal de la aplicación"""
    try:
        # Crear aplicación
        app = QApplication(sys.argv)
        app.setApplicationName("AMPMAuto")
        app.setApplicationVersion("1.0")
        
        # Crear y mostrar ventana principal
        window = MainWindow()
        window.show()
        
        # Ejecutar aplicación
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Error en la aplicación: {str(e)}")
        QMessageBox.critical(None, "Error Crítico", f"La aplicación no pudo iniciarse:\n{str(e)}")

if __name__ == "__main__":
    main()