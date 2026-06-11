# main.py - VERSIÓN CORREGIDA CON GUARDADO COMPLETO Y REINICIO AUTOMÁTICO

import sys
import os
import pandas as pd
from datetime import datetime
import logging
import traceback
import json
import re
import subprocess
import time
import threading

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                                QPushButton, QLabel, QTextEdit, QProgressBar, 
                                QFileDialog, QMessageBox, QWidget, QFrame, 
                                QGroupBox, QTabWidget, QCheckBox, QDialog,
                                QLineEdit, QFormLayout, QDialogButtonBox)
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

    # Importar el DataHandler CORREGIDO desde data_handler.py
    try:
        from data_handler import DataHandler
        DATA_HANDLER_AVAILABLE = True
        print("✅ DataHandler disponible (versión corregida para leer todas las filas)")
    except ImportError as e:
        print(f"Advertencia: No se pudo importar DataHandler: {e}")
        DATA_HANDLER_AVAILABLE = False
        # Crear una versión básica como fallback
        class DataHandler:
            """Manejador de datos para archivos Excel - VERSIÓN BÁSICA"""
            
            def __init__(self, excel_file_path):
                self.excel_file_path = excel_file_path
            
            def read_excel(self):
                """Leer archivo Excel sin encabezados para no perder la primera fila"""
                try:
                    # Leer sin encabezados
                    df = pd.read_excel(self.excel_file_path, header=None)
                    
                    # Buscar números de 11 dígitos en todas las celdas
                    todas_las_guias = []
                    for idx, fila in df.iterrows():
                        for valor in fila:
                            if pd.isna(valor):
                                continue
                            valor_str = str(valor).strip()
                            
                            # Buscar guías de 11 dígitos
                            patron = r'\b\d{11}\b'
                            matches = re.findall(patron, valor_str)
                            
                            for guia in matches:
                                if guia not in todas_las_guias:
                                    todas_las_guias.append(guia)
                    
                    if todas_las_guias:
                        df_final = pd.DataFrame({'numero_guia': todas_las_guias})
                        return df_final
                    else:
                        return pd.DataFrame()
                        
                except Exception as e:
                    print(f"Error leyendo Excel: {str(e)}")
                    return pd.DataFrame()

    # Configurar logging
    logger = setup_logger() if UTILS_AVAILABLE else logging.getLogger(__name__)

    # ════════════════════════════════════════════════════════════════
    #  DeliveryRegistry — registro thread-safe de guías ya entregadas
    # ════════════════════════════════════════════════════════════════
    class DeliveryRegistry:
        """Registro in-memory + archivo de guías entregadas en esta sesión.
        Thread-safe para uso concurrente por múltiples WorkerThreads."""

        def __init__(self):
            appdata = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
            reg_dir = os.path.join(appdata, 'AMPMAuto')
            os.makedirs(reg_dir, exist_ok=True)
            self._path = os.path.join(reg_dir, 'delivered_registry.json')
            self._lock = threading.Lock()
            self._delivered = set()
            self._persist()          # Limpia el archivo al inicio de cada sesión

        def is_delivered(self, guia: str) -> bool:
            with self._lock:
                return str(guia).strip() in self._delivered

        def mark_delivered(self, guia: str):
            with self._lock:
                self._delivered.add(str(guia).strip())
                self._persist()

        def count(self) -> int:
            with self._lock:
                return len(self._delivered)

        def _persist(self):
            try:
                with open(self._path, 'w', encoding='utf-8') as f:
                    json.dump(list(self._delivered), f)
            except Exception:
                pass

    # ════════════════════════════════════════════════════════════════
    #  WorkerThread — un Chrome, un chunk de guías
    # ════════════════════════════════════════════════════════════════
    class WorkerThread(QThread):
        """Procesa un subconjunto de guías con su propio navegador Chrome."""

        guide_result  = pyqtSignal(int, dict)        # (worker_id, result_dict)
        worker_log    = pyqtSignal(int, str)          # (worker_id, mensaje)
        worker_done   = pyqtSignal(int, int, int, int)  # (worker_id, success, error, recovered)

        def __init__(self, worker_id: int, guias_chunk: list,
                     headless: bool, registry: 'DeliveryRegistry'):
            super().__init__()
            self.worker_id    = worker_id
            self.guias_chunk  = guias_chunk
            self.headless     = headless
            self.registry     = registry
            self.is_running   = True
            self._automator   = None

        def run(self):
            prefix  = f"[W{self.worker_id + 1}]"
            success = error = recovered = 0

            try:
                self.worker_log.emit(self.worker_id, f"{prefix} 🚀 Iniciando navegador...")
                self._automator = AMPMAutomator(headless=self.headless)
                self.worker_log.emit(self.worker_id,
                    f"{prefix} ✅ Listo — procesando {len(self.guias_chunk)} guías")

                for guia_data in self.guias_chunk:
                    if not self.is_running:
                        break

                    guia_num = str(guia_data.get('numero_guia', '')).strip().replace('.0', '')

                    # ── Saltar si ya fue entregada por otro worker ──────────
                    if self.registry.is_delivered(guia_num):
                        self.worker_log.emit(self.worker_id,
                            f"{prefix} ⏭ {guia_num} ya entregada (otro worker)")
                        result = {
                            'success': False, 'recoverable': True,
                            'guia_number': guia_num,
                            'error': 'Ya entregada por otro worker',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'processing_time': 0,
                        }
                        recovered += 1
                        self.guide_result.emit(self.worker_id, result)
                        continue

                    # ── Procesar la guía ────────────────────────────────────
                    try:
                        result = self._automator.process_shipment_with_retry(guia_data)
                        result['guia_number'] = guia_num

                        if result.get('success'):
                            success += 1
                            self.registry.mark_delivered(guia_num)
                            self.worker_log.emit(self.worker_id, f"{prefix} ✅ {guia_num}")
                        elif result.get('recoverable'):
                            recovered += 1
                            if 'entregada' in result.get('error', '').lower():
                                self.registry.mark_delivered(guia_num)
                            self.worker_log.emit(self.worker_id,
                                f"{prefix} ⚠️ {guia_num} ya entregada")
                        else:
                            error += 1
                            self.worker_log.emit(self.worker_id,
                                f"{prefix} ❌ {guia_num}: {result.get('error','')[:80]}")

                        self.guide_result.emit(self.worker_id, result)

                    except Exception as exc:
                        error += 1
                        err_result = {
                            'success': False, 'recoverable': False,
                            'guia_number': guia_num,
                            'error': str(exc),
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'processing_time': 0,
                        }
                        self.guide_result.emit(self.worker_id, err_result)
                        self.worker_log.emit(self.worker_id,
                            f"{prefix} ❌ Excepción en {guia_num}: {exc}")

            except Exception as fatal:
                self.worker_log.emit(self.worker_id,
                    f"{prefix} 💥 Error fatal del worker: {fatal}")

            finally:
                if self._automator:
                    try:
                        self._automator.close()
                    except Exception:
                        pass

            self.worker_log.emit(self.worker_id,
                f"{prefix} 🏁 Terminado — ✅{success} ⚠️{recovered} ❌{error}")
            self.worker_done.emit(self.worker_id, success, error, recovered)

        def stop(self):
            self.is_running = False
            if self._automator:
                try:
                    self._automator.driver.quit()
                except Exception:
                    pass

    # ════════════════════════════════════════════════════════════════
    #  AutomationThread — coordinador que lanza N workers en paralelo
    # ════════════════════════════════════════════════════════════════
    class AutomationThread(QThread):
        """Divide las guías en chunks, lanza N workers Chrome en paralelo y
        agrega sus resultados en los mismos signals que espera la UI."""

        progress_updated = pyqtSignal(int, str)   # (porcentaje 0-100, mensaje)
        log_message      = pyqtSignal(str)
        finished_success = pyqtSignal(dict)
        finished_error   = pyqtSignal(str)

        N_WORKERS = 3

        def __init__(self, excel_file_path: str, headless: bool = True):
            super().__init__()
            self.excel_file_path = excel_file_path
            self.headless        = headless
            self.is_running      = True
            self._workers        = []
            # Contadores thread-safe
            self._lock      = threading.Lock()
            self._success   = 0
            self._error     = 0
            self._recovered = 0
            self._done      = 0
            self._total     = 0
            self._all_results = []

        def run(self):
            try:
                self.log_message.emit("📊 Leyendo archivo Excel...")
                data_handler = DataHandler(self.excel_file_path)
                guias_df = data_handler.read_excel()

                if guias_df.empty:
                    self.finished_error.emit(
                        "El archivo Excel está vacío o no contiene guías válidas de 11 dígitos")
                    return

                guias_list = [row for _, row in guias_df.iterrows()]
                total = len(guias_list)
                self._total = total

                self.log_message.emit(
                    f"📦 {total} guías encontradas — dividiendo en {self.N_WORKERS} workers")

                # Dividir en chunks contiguos
                chunk_size = (total + self.N_WORKERS - 1) // self.N_WORKERS
                chunks = [guias_list[i * chunk_size:(i + 1) * chunk_size]
                          for i in range(self.N_WORKERS)]
                chunks = [c for c in chunks if c]   # Eliminar chunks vacíos
                n_actual = len(chunks)

                for i, chunk in enumerate(chunks):
                    self.log_message.emit(f"  🔸 Worker {i + 1}: {len(chunk)} guías")

                # Registro compartido entre todos los workers
                registry = DeliveryRegistry()

                # Crear workers
                self._workers = []
                for i, chunk in enumerate(chunks):
                    w = WorkerThread(i, chunk, self.headless, registry)
                    # DirectConnection: el slot corre en el hilo del worker,
                    # sin necesidad de un event loop en AutomationThread.run()
                    w.guide_result.connect(self._on_guide_result, Qt.DirectConnection)
                    w.worker_log.connect(self._on_worker_log,     Qt.DirectConnection)
                    w.worker_done.connect(self._on_worker_done,   Qt.DirectConnection)
                    self._workers.append(w)

                self.log_message.emit(f"🚀 Lanzando {n_actual} navegadores en paralelo...")
                for w in self._workers:
                    w.start()

                # Esperar a que todos terminen
                for w in self._workers:
                    w.wait()

                if not self.is_running:
                    return   # Detenido por el usuario; _on_automation_stopped lo maneja

                # Construir reporte final
                with self._lock:
                    final_success   = self._success
                    final_error     = self._error
                    final_recovered = self._recovered
                    final_results   = list(self._all_results)

                report = {
                    'total':      total,
                    'success':    final_success,
                    'errors':     final_error + final_recovered,
                    'recovered':  final_recovered,
                    'results':    final_results,
                    'timestamp':  datetime.now(),
                    'excel_file': self.excel_file_path,
                }
                self.finished_success.emit(report)

            except Exception as exc:
                self.finished_error.emit(
                    f"Error en el proceso: {exc}\n{traceback.format_exc()}")

        # ── Slots vía DirectConnection (ejecutan en el hilo del worker) ─────

        def _on_guide_result(self, worker_id: int, result: dict):
            with self._lock:
                self._done += 1
                self._all_results.append(result)
                done  = self._done
                total = self._total
                if result.get('success'):
                    self._success += 1
                elif result.get('recoverable'):
                    self._recovered += 1
                else:
                    self._error += 1

            pct    = int(done / total * 100) if total else 0
            guia   = result.get('guia_number', '')
            icon   = '✅' if result.get('success') else ('⚠️' if result.get('recoverable') else '❌')
            self.progress_updated.emit(pct,
                f"{icon} [{worker_id + 1}] {guia} — {done}/{total}")

        def _on_worker_log(self, worker_id: int, msg: str):
            self.log_message.emit(msg)

        def _on_worker_done(self, worker_id: int, success: int,
                            error: int, recovered: int):
            # Los contadores ya se actualizan en _on_guide_result;
            # este signal solo sirve para el log de cierre del worker.
            pass

        # ────────────────────────────────────────────────────────────

        def stop(self):
            """Detener todos los workers"""
            self.is_running = False
            for w in self._workers:
                w.stop()
            self.log_message.emit("⏹️ Proceso detenido por el usuario")

        def sleep(self, seconds):
            """Compatibilidad — no usado en modo paralelo"""
            for _ in range(int(seconds * 20)):
                if not self.is_running:
                    break
                QThread.msleep(50)

    class PasswordDialog(QDialog):
        """Diálogo para ingresar la contraseña de administrador"""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Contraseña requerida")
            self.setModal(True)
            self.password = None
            
            layout = QVBoxLayout()
            self.setLayout(layout)
            
            self.label = QLabel("Ingrese la contraseña de administrador:")
            layout.addWidget(self.label)
            
            self.password_edit = QLineEdit()
            self.password_edit.setEchoMode(QLineEdit.Password)
            layout.addWidget(self.password_edit)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
        
        def accept(self):
            self.password = self.password_edit.text()
            super().accept()

    class CredentialsDialog(QDialog):
        def __init__(self, config_manager, parent=None):
            super().__init__(parent)
            self.config = config_manager
            self.setWindowTitle("Editar configuración AMPM")
            self.setModal(True)
            
            layout = QVBoxLayout()
            self.setLayout(layout)
            
            # Información sobre la ubicación del archivo
            file_info = QLabel(f"Archivo de configuración: {self.config.env_file}")
            file_info.setStyleSheet("color: #666; font-size: 10px;")
            file_info.setWordWrap(True)
            layout.addWidget(file_info)
            
            form_layout = QFormLayout()
            
            # Convenio
            self.convenio_edit = QLineEdit()
            self.convenio_edit.setText(self.config.ampm_convenio)
            form_layout.addRow("Convenio:", self.convenio_edit)
            
            # Usuario
            self.username_edit = QLineEdit()
            self.username_edit.setText(self.config.ampm_username)
            form_layout.addRow("Usuario:", self.username_edit)
            
            # Contraseña
            self.password_edit = QLineEdit()
            self.password_edit.setText(self.config.ampm_password)
            self.password_edit.setEchoMode(QLineEdit.Password)
            form_layout.addRow("Contraseña:", self.password_edit)
            
            # URL de AMPM
            self.url_edit = QLineEdit()
            self.url_edit.setText(self.config.ampm_url)
            form_layout.addRow("URL de AMPM:", self.url_edit)
            
            # Tooltip para la URL
            self.url_edit.setToolTip("URL completa de acceso a AMPM\nEjemplo: https://convenios.grupoampm.com/Convenio/Login?returnUrl=/")
            
            layout.addLayout(form_layout)
            
            buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
            buttons.accepted.connect(self.save)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
        
        def save(self):
            """Guardar los cambios"""
            # Validar campos obligatorios
            if not self.convenio_edit.text().strip():
                QMessageBox.warning(self, "Campo requerido", "El convenio es obligatorio")
                return
                
            if not self.username_edit.text().strip():
                QMessageBox.warning(self, "Campo requerido", "El usuario es obligatorio")
                return
                
            if not self.password_edit.text().strip():
                QMessageBox.warning(self, "Campo requerido", "La contraseña es obligatoria")
                return
                
            if not self.url_edit.text().strip():
                QMessageBox.warning(self, "Campo requerido", "La URL es obligatoria")
                return
            
            # Guardar las credenciales
            success = self.config.save_credentials(
                self.convenio_edit.text().strip(),
                self.username_edit.text().strip(),
                self.password_edit.text().strip(),
                self.url_edit.text().strip()
            )
            
            if success:
                # Mostrar mensaje con la ubicación del archivo
                QMessageBox.information(
                    self,
                    "Configuración guardada",
                    f"✅ Configuración actualizada exitosamente.\n\n"
                    f"Archivo guardado en:\n{self.config.env_file}\n\n"
                    f"La aplicación se reiniciará para aplicar los cambios."
                )
                self.accept()
            else:
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"No se pudieron guardar las credenciales.\n\n"
                    f"Verifica que tengas permisos de escritura en:\n{self.config.env_file}"
                )

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
        background-color: #f8f9fa;
        color: #212529;
        border: 2px solid #ced4da;
        border-radius: 8px;
        padding: 15px;
        font-family: Consolas, monospace;
        font-size: 14pt;
        font-weight: 500;
        line-height: 1.4;
        selection-background-color: #007bff;
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
            """Crear la pestaña de configuración - MODIFICADO PARA INCLUIR BOTÓN DE CREDENCIALES"""
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
            
            # Botón para editar credenciales AMPM
            credentials_btn = QPushButton("🔐 Editar configuración AMPM")
            credentials_btn.clicked.connect(self.edit_credentials)
            credentials_btn.setMinimumHeight(40)
            credentials_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            config_layout.addWidget(credentials_btn)
            
            # Información del sistema
            # En el método create_config_tab, modifica system_info:
            system_info = f"""
AMPMAuto v1.4.0 - VERSIÓN RÁPIDA
Desarrollado por: Kevin Brian Ibarra Pineda ISIC
Python: {sys.version.split()[0]}
Directorio de trabajo: {os.getcwd()}

CONFIGURACIÓN ACTUAL:
• Archivo .env: {self.config.env_file}
• Convenio: {self.config.ampm_convenio}
• Usuario: {self.config.ampm_username}
• URL: {self.config.ampm_url[:50]}...

Módulos disponibles:
• PyQt5: {'✅' if PYQT5_AVAILABLE else '❌'}
• Automator: {'✅' if AUTOMATOR_AVAILABLE else '❌'}
• ReportGenerator: {'✅' if REPORT_GENERATOR_AVAILABLE else '❌'}
• Utils: {'✅' if UTILS_AVAILABLE else '❌'}
• DataHandler: {'✅' if DATA_HANDLER_AVAILABLE else '❌'}

Características:
• Manejo robusto de errores
• Detección automática de modales  
• Reintentos inteligentes
• Reportes Excel detallados
• Filtrado automático de guías inválidas
• Manejo mejorado de loading
• Generación automática de reportes Excel
• OPTIMIZADO PARA VELOCIDAD: 10-15 guías/minuto
• ✅ CORRECCIÓN: Lee TODAS las filas incluyendo la primera
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
        
        def edit_credentials(self):
            """Abrir diálogo para editar credenciales AMPM"""
            # Primero, pedir la contraseña de administrador
            password_dialog = PasswordDialog(self)
            if password_dialog.exec_() == QDialog.Accepted:
                if password_dialog.password != "KillerQueen498":
                    QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña ingresada es incorrecta.")
                    return
            
            # Si la contraseña es correcta, mostrar el diálogo de credenciales
            cred_dialog = CredentialsDialog(self.config, self)
            if cred_dialog.exec_() == QDialog.Accepted:
                reply = QMessageBox.question(
                    self,
                    "Reinicio requerido",
                    "✅ Configuración actualizada exitosamente.\n\n"
                    "Para aplicar los cambios, la aplicación necesita reiniciarse.\n\n"
                    "¿Deseas reiniciar ahora?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.restart_application()
        
        def restart_application(self):
            """Reiniciar la aplicación automáticamente"""
            try:
                self.add_log_message("🔄 Reiniciando aplicación...")
                self.add_log_message("⚠️ Por favor espera unos segundos...")
                
                # Cerrar la ventana actual
                self.close()
                
                # Esperar un momento para que se cierre correctamente
                QApplication.processEvents()
                time.sleep(2)
                
                # Reiniciar la aplicación
                if sys.platform == "win32":
                    # Para Windows
                    subprocess.Popen([sys.executable] + sys.argv)
                else:
                    # Para Linux/Mac
                    os.execl(sys.executable, sys.executable, *sys.argv)
                
                # Salir de la aplicación actual
                QApplication.quit()
                
            except Exception as e:
                self.add_log_message(f"❌ Error al reiniciar: {str(e)}")
                QMessageBox.warning(
                    self,
                    "Reinicio manual requerido",
                    "No se pudo reiniciar automáticamente.\n\n"
                    "Por favor cierra y vuelve a abrir la aplicación manualmente."
                )
        
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
                
                # Mostrar preview del archivo usando el DataHandler corregido
                try:
                    # Usar el DataHandler corregido que lee TODAS las filas
                    data_handler = DataHandler(file_path)
                    df_clean = data_handler.read_excel()
                    clean_count = len(df_clean)
                    
                    # Leer también el archivo original para comparar
                    df_original = pd.read_excel(file_path, header=None)
                    original_count = 0
                    
                    # Contar celdas que podrían contener guías en el original
                    for idx, fila in df_original.iterrows():
                        for valor in fila:
                            if pd.isna(valor):
                                continue
                            valor_str = str(valor).strip()
                            if re.search(r'\d{11}', valor_str):
                                original_count += 1
                    
                    self.add_log_message(f"📊 Archivo original: {original_count} posibles guías detectadas")
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
            self.add_log_message("✅ CORRECCIÓN APLICADA: Ahora se lee TODAS las filas incluyendo la primera")
        
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