# automator.py - VERSIÓN MEJORADA CON MANEJO DE NAN Y LOADING
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import logging
import os
import pandas as pd
import re
from utils.config import ConfigManager

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AMPMAutomatorRobusto:
    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.config = ConfigManager()
        self.is_logged_in = False
        self.max_processing_time = 30
        self.retry_count = 0
        self.max_retries = 3
        self.init_driver()
    
    def init_driver(self):
        """Inicializar el WebDriver de Chrome"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless=new")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.set_page_load_timeout(30)
            self.driver.set_script_timeout(30)
            
            self.wait = WebDriverWait(self.driver, 15)
            logger.info("✅ Navegador Chrome inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar el navegador: {str(e)}")
            raise
    
    def _wait_for_loading_to_disappear(self, timeout=10):
        """Esperar a que desaparezca el elemento de loading - NUEVA FUNCIÓN"""
        try:
            logger.info("⏳ Esperando a que desaparezca el loading...")
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((By.ID, "divLoading"))
            )
            logger.info("✅ Loading desapareció")
        except TimeoutException:
            logger.warning("⚠️ Timeout esperando loading, continuando...")
        except Exception as e:
            logger.warning(f"⚠️ Error verificando loading: {e}")
    
    def check_and_close_modals(self):
        """Verificar y cerrar modales específicos de AMPM - MEJORADO"""
        try:
            # Patrones de mensajes que indican guía ya entregada o problemas
            modal_patterns = [
                "La guía ya se encuentra entregada",
                "guía ya se encuentra entregada", 
                "ya se encuentra entregada",
                "guía entregada",
                "no es válida",
                "error",
                "inválida"
            ]
            
            # Buscar modales visibles
            modal_selectors = [
                "//div[contains(@class, 'ui-dialog') and contains(@style, 'display: block')]",
                "//div[@role='dialog' and contains(@style, 'display: block')]",
                "//div[contains(@class, 'ui-dialog')]//*[contains(text(), 'guía')]",
                "//div[@id='errorTPAK']",
                "//div[contains(@class, 'ui-dialog-title') and contains(text(), 'TPAK')]"
            ]
            
            for selector in modal_selectors:
                try:
                    modals = self.driver.find_elements(By.XPATH, selector)
                    for modal in modals:
                        if modal.is_displayed():
                            # Obtener el texto del modal para diagnóstico
                            modal_text = modal.text
                            logger.info(f"🔍 Modal detectado: {modal_text[:100]}...")
                            
                            # Verificar si es el modal de "guía ya entregada"
                            for pattern in modal_patterns:
                                if pattern.lower() in modal_text.lower():
                                    logger.warning(f"⚠️ Modal de guía ya entregada detectado: {pattern}")
                                    return self.close_modal_safely(modal, "guía ya entregada")
                            
                            # Cerrar cualquier modal visible
                            return self.close_modal_safely(modal, "modal genérico")
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Error al verificar modales: {str(e)}")
            return False
    
    def close_modal_safely(self, modal, modal_type="modal"):
        """Cerrar modal de manera segura"""
        try:
            logger.info(f"🔄 Cerrando modal de {modal_type}...")
            
            # Estrategia 1: Buscar botón "Ok" en el modal
            ok_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(@class, 'ui-button') and (contains(text(), 'Ok') or contains(text(), 'OK') or contains(text(), 'Aceptar'))]")
            
            for button in ok_buttons:
                if button.is_displayed():
                    self.driver.execute_script("arguments[0].click();", button)
                    logger.info("✅ Modal cerrado con botón Ok")
                    time.sleep(1)
                    return True
            
            # Estrategia 2: Buscar botón de cerrar (X)
            close_buttons = self.driver.find_elements(By.XPATH,
                "//button[contains(@class, 'ui-dialog-titlebar-close')] | "
                "//span[contains(@class, 'ui-icon-closethick')] | "
                "//button[@aria-label='close']")
            
            for button in close_buttons:
                if button.is_displayed():
                    self.driver.execute_script("arguments[0].click();", button)
                    logger.info("✅ Modal cerrado con botón X")
                    time.sleep(1)
                    return True
            
            # Estrategia 3: Presionar ESC
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.ESCAPE).perform()
            logger.info("✅ Intentando cerrar modal con ESC")
            time.sleep(1)
            
            # Estrategia 4: Click fuera del modal
            try:
                overlay = self.driver.find_element(By.CLASS_NAME, "ui-widget-overlay")
                if overlay.is_displayed():
                    self.driver.execute_script("arguments[0].click();", overlay)
                    logger.info("✅ Modal cerrado clickeando fuera")
                    time.sleep(1)
            except:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al cerrar modal: {str(e)}")
            return False
    
    def safe_clear_and_send_keys(self, element, text):
        """Método seguro para limpiar y enviar texto a un elemento"""
        try:
            # Primero verificar y cerrar modales
            self.check_and_close_modals()
            
            # Hacer scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            
            # Limpiar campo
            element.clear()
            time.sleep(0.2)
            
            # Enviar texto
            element.send_keys(text)
            time.sleep(0.5)
            
            return True
            
        except (ElementNotInteractableException, StaleElementReferenceException) as e:
            logger.warning(f"⚠️ Elemento no interactuable, verificando modales...")
            self.check_and_close_modals()
            return False
    
    def safe_click(self, element, description="elemento"):
        """Click seguro que verifica modales primero"""
        try:
            # Verificar modales antes de hacer click
            if self.check_and_close_modals():
                logger.info("🔄 Modal cerrado antes del click")
                time.sleep(1)
            
            # Hacer scroll al elemento
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            
            if element.is_displayed() and element.is_enabled():
                element.click()
                logger.info(f"✅ Click exitoso en {description}")
                
                # Verificar si apareció algún modal después del click
                time.sleep(1)
                self.check_and_close_modals()
                
                return True
            else:
                logger.warning(f"⚠️ Elemento {description} no está interactuable")
                return False
                
        except (ElementNotInteractableException, StaleElementReferenceException) as e:
            logger.warning(f"⚠️ Error al hacer click en {description}, verificando modales...")
            self.check_and_close_modals()
            return False
    
    def handle_errors(self):
        """Manejar errores de validación en la página - MEJORADO"""
        try:
            # Primero verificar modales
            if self.check_and_close_modals():
                return "Modal de error detectado y cerrado"
            
            # Verificar errores de campo específicos
            field_errors = self.driver.find_elements(By.CLASS_NAME, "field-validation-error")
            visible_field_errors = [elem for elem in field_errors if elem.is_displayed() and elem.text.strip()]
            
            if visible_field_errors:
                error_text = visible_field_errors[0].text
                logger.error(f"❌ Error de validación: {error_text}")
                return error_text
            
            # Verificar mensajes de éxito para evitar falsos positivos
            success_elements = self.driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'éxito') or contains(text(), 'exitosamente') or contains(text(), 'success')]")
            if success_elements and any(elem.is_displayed() for elem in success_elements):
                return None
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Error al verificar errores: {str(e)}")
            return None

    def login(self):
        """Iniciar sesión en el portal AMPM"""
        try:
            logger.info("🔐 Iniciando sesión en AMPM...")
            
            username = self.config.ampm_username
            password = self.config.ampm_password
            login_url = "https://tpak.grupoampm.com/Convenio/Login?returnUrl=/"
            
            if not username or not password:
                raise Exception("Credenciales de AMPM no configuradas en el archivo .env")
            
            self.driver.get(login_url)
            logger.info(f"🌐 Navegando a: {login_url}")
            
            self.wait.until(EC.presence_of_element_located((By.ID, "ConvenioId")))
            
            convenio_field = self.driver.find_element(By.ID, "ConvenioId")
            convenio_field.clear()
            convenio_field.send_keys("0")
            
            username_field = self.driver.find_element(By.ID, "UserName")
            username_field.clear()
            username_field.send_keys(username)
            
            password_field = self.driver.find_element(By.ID, "Contrasenia")
            password_field.clear()
            password_field.send_keys(password)
            
            login_button = self.driver.find_element(By.XPATH, "//input[@type='submit' and @value='Acceder']")
            login_button.click()
            
            time.sleep(3)
            
            if any(indicator in self.driver.current_url for indicator in ['/', 'Inicio']):
                logger.info("✅ Login exitoso en AMPM")
                self.is_logged_in = True
                return True
            else:
                error_elements = self.driver.find_elements(By.CLASS_NAME, "field-validation-error")
                if error_elements:
                    error_text = error_elements[0].text
                    logger.error(f"❌ Error en login: {error_text}")
                    return False
                else:
                    logger.warning("⚠️ No se pudo verificar el login, continuando...")
                    self.is_logged_in = True
                    return True
                    
        except Exception as e:
            logger.error(f"❌ Error en login: {str(e)}")
            self.is_logged_in = False
            return False
    
    def navigate_to_shipments(self):
        """Navegar a la sección de entregas"""
        try:
            logger.info("📦 Navegando a la sección de entregas...")
            
            time.sleep(2)
            
            entregas_menu = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//h3[contains(text(), 'Entregas')]"))
            )
            self.driver.execute_script("arguments[0].click();", entregas_menu)
            logger.info("✅ Menú Entregas expandido")
            
            time.sleep(1)
            
            capturar_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[@href='/EntregaEnvio/Entregar' and contains(text(), 'Capturar Confirmaciones')]"))
            )
            self.driver.execute_script("arguments[0].click();", capturar_link)
            logger.info("✅ Navegando a Capturar Confirmaciones")
            
            self.wait.until(EC.presence_of_element_located((By.ID, "GuiaId")))
            logger.info("✅ Página de captura de guías cargada correctamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al navegar a entregas: {str(e)}")
            return False

    def _process_single_shipment_with_timeout(self, guia_data):
        """Procesa una guía individual con manejo de modales - VERSIÓN MEJORADA"""
        import time
        start_time = time.time()
        
        guia_number = guia_data.get('numero_guia', 'N/A')
        
        # ✅ MEJOR VALIDACIÓN DE GUÍAS VACÍAS O INVÁLIDAS
        guia_str = str(guia_number).strip() if guia_number is not None else ''
        
        if (not guia_str or 
            guia_str.lower() in ['nan', 'none', 'null', ''] or
            guia_str == 'N/A' or
            pd.isna(guia_number)):
            
            logger.warning(f"⚠️ Guía vacía o inválida detectada: '{guia_number}' - Saltando...")
            return {
                'success': False,
                'guia_number': 'INVÁLIDA',
                'error': "Número de guía vacío o inválido",
                'recoverable': True,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Remover .0 de números flotantes
        guia_final = guia_str.replace('.0', '') if '.0' in guia_str else guia_str
        logger.info(f"📦 Procesando guía: {guia_final}")
        
        def check_timeout():
            if time.time() - start_time > self.max_processing_time:
                raise TimeoutException(f"Guía tardó más de {self.max_processing_time} segundos")
        
        check_timeout()
        
        if not self.is_logged_in:
            if not self.login():
                return {'success': False, 'error': 'No se pudo iniciar sesión'}
        
        check_timeout()
        
        if "EntregaEnvio/Entregar" not in self.driver.current_url:
            if not self.navigate_to_shipments():
                return {'success': False, 'error': 'No se pudo navegar a la sección de entregas'}
        
        check_timeout()
        
        try:
            # Obtener el campo de guía
            guia_field = self.wait.until(EC.presence_of_element_located((By.ID, "GuiaId")))
            
            # Verificar modales antes de ingresar la guía
            self.check_and_close_modals()
            
            # Ingresar guía
            if not self.safe_clear_and_send_keys(guia_field, guia_final):
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "No se pudo ingresar el número de guía"
                }
            
            logger.info(f"✅ Guía {guia_final} ingresada, esperando detalles...")
            
            # Presionar Enter para buscar
            guia_field.send_keys(Keys.ENTER)
            
            check_timeout()
            time.sleep(4)  # Esperar a que carguen los detalles
            
            # Verificar si apareció el modal de "guía ya entregada"
            if self.check_and_close_modals():
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía ya se encuentra entregada",
                    'recoverable': True
                }
            
            check_timeout()
            
            # Verificar otros errores
            error_message = self.handle_errors()
            if error_message:
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': f"Error en guía: {error_message}",
                    'recoverable': "entregada" in error_message.lower()
                }
            
            check_timeout()
            
            # ✅ ESPERAR A QUE DESAPAREZCA EL LOADING ANTES DE HACER CLICK
            self._wait_for_loading_to_disappear()
            
            # Buscar botón Entregar
            entregar_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btnEntregar"))
            )
            
            if not self.safe_click(entregar_button, "botón Entregar"):
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "No se pudo hacer click en el botón Entregar"
                }
            
            logger.info(f"✅ Botón Entregar presionado para guía {guia_final}")
            
            check_timeout()
            
            # ✅ ESPERAR PROCESAMIENTO Y VERIFICAR LOADING
            self._wait_for_loading_to_disappear()
            time.sleep(2)  # Espera adicional
            
            # Verificar modales después de entregar
            if self.check_and_close_modals():
                return {
                    'success': False, 
                    'guia_number': guia_final,
                    'error': "Error al entregar - modal detectado",
                    'recoverable': True
                }
            
            # Verificar errores después de entregar
            error_message = self.handle_errors()
            if error_message:
                recoverable = any(pattern in error_message.lower() for pattern in 
                                ['entregada', 'duplicada', 'repetida'])
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': f"Error al entregar: {error_message}",
                    'recoverable': recoverable
                }
            
            logger.info(f"✅ Guía {guia_final} procesada exitosamente")
            
            # Limpiar campos para siguiente guía
            try:
                nuevo_button = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "btnNuevo"))
                )
                if self.safe_click(nuevo_button, "botón Nuevo"):
                    logger.info("✅ Campos limpiados con botón Nuevo")
                    time.sleep(1)
            except:
                logger.info("ℹ️ No se encontró el botón Nuevo")
            
            processing_time = time.time() - start_time
            logger.info(f"⏱️ Tiempo de procesamiento: {processing_time:.2f} segundos")
            
            return {
                'success': True,
                'guia_number': guia_final,
                'message': 'Guía registrada exitosamente en AMPM',
                'processing_time': processing_time,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento de guía {guia_final}: {str(e)}")
            # Intentar recuperar el estado
            self.check_and_close_modals()
            raise
    
    def process_shipment_with_retry(self, guia_data):
        """Procesar guía con reintentos inteligentes"""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔄 Intento {attempt + 1}/{self.max_retries + 1} para guía [CONFIDENCIAL]")
                
                result = self._process_single_shipment_with_timeout(guia_data)
                
                if result['success']:
                    return result
                elif result.get('recoverable', False):
                    logger.info("🔄 Error recuperable, continuando con siguiente guía")
                    return result
                elif attempt < self.max_retries:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"⏳ Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    return result
                    
            except Exception as e:
                error_msg = str(e)
                if attempt < self.max_retries:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"⏳ Error: {error_msg}. Reintentando en {wait_time} segundos...")
                    time.sleep(wait_time)
                else:
                    return {
                        'success': False,
                        'guia_number': '[CONFIDENCIAL]',
                        'error': f"Error después de {self.max_retries + 1} intentos: {error_msg}",
                        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
    
    def close(self):
        """Cerrar el navegador"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("🔒 Navegador cerrado")
            except:
                pass

# COMENTADO: Función de prueba removida para distribución
"""
# FUNCIÓN DE PRUEBA ESPECÍFICA PARA MODALES
def test_ampm_modal_fix():
    # ... código de prueba comentado ...
    pass

if __name__ == "__main__":
    # Ejecutar prueba específica para modales
    test_ampm_modal_fix()
"""