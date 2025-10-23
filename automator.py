# automator.py - VERSIÓN CORREGIDA CON DETECCIÓN MEJORADA DE GUÍAS ENTREGADAS
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
        """Esperar a que desaparezca el elemento de loading"""
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
        """Verificar y cerrar modales específicos de AMPM - VERSIÓN MEJORADA"""
        try:
            # PATRONES MÁS COMPLETOS para guías ya entregadas
            modal_patterns = [
                "La guía ya se encuentra entregada",
                "guía ya se encuentra entregada", 
                "ya se encuentra entregada",
                "guía entregada",
                "la guía ya fue entregada",
                "guía ya fue entregada", 
                "ya fue entregada",
                "no es válida",
                "error",
                "inválida",
                "no ha sido asignada a ninguno de los convenios",
                "no ha sido asignada",
                "convenios que administra esta cuenta"
            ]
            
            # MÁS SELECTORES para capturar todos los modales posibles
            modal_selectors = [
                "//div[contains(@class, 'ui-dialog') and contains(@style, 'display: block')]",
                "//div[@role='dialog' and contains(@style, 'display: block')]",
                "//div[contains(@class, 'ui-dialog')]//*[contains(text(), 'guía')]",
                "//div[@id='errorTPAK']",
                "//div[contains(@class, 'ui-dialog-title') and contains(text(), 'TPAK')]",
                "//div[contains(@class, 'ui-dialog-content')]//p[contains(text(), 'guía')]",
                "//div[contains(@class, 'modal')]",
                "//div[contains(@class, 'popup')]",
                "//div[contains(@style, 'display: block')]//*[contains(text(), 'guía')]"
            ]
            
            modal_detected = False
            modal_text_content = ""
            
            for selector in modal_selectors:
                try:
                    modals = self.driver.find_elements(By.XPATH, selector)
                    for modal in modals:
                        if modal.is_displayed():
                            modal_text = modal.text
                            logger.info(f"🔍 Modal detectado: {modal_text[:100]}...")
                            modal_text_content = modal_text
                            
                            # VERIFICACIÓN MÁS ESTRICTA de guía ya entregada
                            for pattern in modal_patterns:
                                if pattern.lower() in modal_text.lower():
                                    logger.warning(f"⚠️ Modal de '{pattern}' detectado")
                                    
                                    # GUÍA NO ASIGNADA
                                    if any(p in modal_text.lower() for p in ["no ha sido asignada", "convenios que administra"]):
                                        logger.error("❌ GUÍA NO ASIGNADA AL CONVENIO DETECTADA")
                                        self.close_modal_safely(modal, "guía no asignada")
                                        return "guia_no_asignada"
                                    
                                    # GUÍA YA ENTREGADA
                                    if any(p in modal_text.lower() for p in ["entregada", "ya se encuentra", "ya fue"]):
                                        logger.error("❌ GUÍA YA ENTREGADA DETECTADA")
                                        self.close_modal_safely(modal, "guía ya entregada")
                                        return "guia_ya_entregada"
                                    
                                    # OTRO ERROR
                                    self.close_modal_safely(modal, "error genérico")
                                    return True
                            
                            # Cerrar cualquier modal visible
                            self.close_modal_safely(modal, "modal genérico")
                            modal_detected = True
                except Exception as e:
                    continue
            
            # BÚSQUEDA EN HTML COMPLETO como respaldo
            try:
                page_source = self.driver.page_source.lower()
                if "no ha sido asignada a ninguno de los convenios" in page_source:
                    logger.error("❌ MENSAJE 'GUÍA NO ASIGNADA' DETECTADO EN HTML")
                    return "guia_no_asignada"
                elif "ya se encuentra entregada" in page_source:
                    logger.error("❌ MENSAJE 'GUÍA YA ENTREGADA' DETECTADO EN HTML")
                    return "guia_ya_entregada"
            except:
                pass
                
            return modal_detected
            
        except Exception as e:
            logger.warning(f"⚠️ Error al verificar modales: {str(e)}")
            return False
    
    def close_modal_safely(self, modal, modal_type="modal"):
        """Cerrar modal de manera segura"""
        try:
            logger.info(f"🔄 Cerrando modal de {modal_type}...")
            
            # MÚLTIPLES ESTRATEGIAS de cierre
            close_strategies = [
                # Botones Ok/Aceptar
                lambda: self._click_element_by_xpath(
                    "//button[contains(@class, 'ui-button') and (contains(text(), 'Ok') or contains(text(), 'OK') or contains(text(), 'Aceptar'))]"
                ),
                # Botones Cerrar (X)
                lambda: self._click_element_by_xpath(
                    "//button[contains(@class, 'ui-dialog-titlebar-close')] | "
                    "//span[contains(@class, 'ui-icon-closethick')] | "
                    "//button[@aria-label='close']"
                ),
                # Presionar ESC
                lambda: ActionChains(self.driver).send_keys(Keys.ESCAPE).perform(),
                # Click fuera del modal
                lambda: self._click_element_by_class("ui-widget-overlay")
            ]
            
            for strategy in close_strategies:
                try:
                    if strategy():
                        logger.info(f"✅ Modal cerrado con estrategia {close_strategies.index(strategy) + 1}")
                        time.sleep(1)
                        return True
                except:
                    continue
                
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al cerrar modal: {str(e)}")
            return False
    
    def _click_element_by_xpath(self, xpath):
        """Helper para clickear elementos por XPATH"""
        elements = self.driver.find_elements(By.XPATH, xpath)
        for element in elements:
            if element.is_displayed():
                self.driver.execute_script("arguments[0].click();", element)
                return True
        return False
    
    def _click_element_by_class(self, class_name):
        """Helper para clickear elementos por clase"""
        try:
            element = self.driver.find_element(By.CLASS_NAME, class_name)
            if element.is_displayed():
                self.driver.execute_script("arguments[0].click();", element)
                return True
        except:
            pass
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
            modal_result = self.check_and_close_modals()
            if modal_result:
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
            modal_result = self.check_and_close_modals()
            if modal_result == "guia_no_asignada":
                return "La guía no está asignada al convenio"
            elif modal_result == "guia_ya_entregada":
                return "La guía ya se encuentra entregada"
            elif modal_result:
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
        """Procesa una guía individual con manejo de modales - VERSIÓN COMPLETAMENTE CORREGIDA"""
        import time
        start_time = time.time()
        
        guia_number = guia_data.get('numero_guia', 'N/A')
        
        # ✅ VALIDACIÓN DE GUÍAS VACÍAS O INVÁLIDAS
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
            modal_result = self.check_and_close_modals()
            
            # Manejar casos específicos de modales
            if modal_result == "guia_no_asignada":
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía no está asignada al convenio",
                    'recoverable': False,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            elif modal_result == "guia_ya_entregada":
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía ya se encuentra entregada",
                    'recoverable': True,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            
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
            
            # VERIFICACIÓN DESPUÉS DE INGRESAR GUÍA
            modal_result = self.check_and_close_modals()
            if modal_result == "guia_no_asignada":
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía no está asignada al convenio",
                    'recoverable': False
                }
            elif modal_result == "guia_ya_entregada":
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía ya se encuentra entregada",
                    'recoverable': True
                }
            
            check_timeout()
            
            # ✅ VERIFICACIÓN EN HTML COMPLETO
            page_source = self.driver.page_source
            if "no ha sido asignada a ninguno de los convenios" in page_source.lower():
                logger.error(f"❌ Guía {guia_final} no asignada al convenio (detectado en HTML)")
                self.check_and_close_modals()
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía no está asignada al convenio",
                    'recoverable': False,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            elif "ya se encuentra entregada" in page_source.lower():
                logger.error(f"❌ Guía {guia_final} ya entregada (detectado en HTML)")
                self.check_and_close_modals()
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía ya se encuentra entregada",
                    'recoverable': True,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # ✅ ESPERAR A QUE DESAPAREZCA EL LOADING ANTES DE HACER CLICK - DESCOMENTADO
            self._wait_for_loading_to_disappear()

            # ✅ BUSCAR Y HACER CLIC EN BOTÓN ENTREGAR - DESCOMENTADO Y MEJORADO
            try:
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
            except Exception as e:
                logger.error(f"❌ No se pudo encontrar el botón Entregar: {str(e)}")
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': f"No se pudo encontrar el botón Entregar: {str(e)}",
                    'recoverable': False
                }
            
            check_timeout()
            
            # ✅ ESPERAR PROCESAMIENTO Y VERIFICAR LOADING
            self._wait_for_loading_to_disappear()
            time.sleep(3)  # Espera adicional después de entregar
            
            # ✅ VERIFICACIÓN EXHAUSTIVA DESPUÉS DE ENTREGAR
            modal_result = self.check_and_close_modals()
            if modal_result == "guia_no_asignada":
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía no está asignada al convenio",
                    'recoverable': False
                }
            elif modal_result == "guia_ya_entregada":
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía ya se encuentra entregada",
                    'recoverable': True
                }
            elif modal_result:
                return {
                    'success': False, 
                    'guia_number': guia_final,
                    'error': "Error al entregar - modal detectado",
                    'recoverable': True
                }
            
            # ✅ VERIFICACIÓN FINAL EN HTML
            page_source = self.driver.page_source.lower()
            if "no ha sido asignada" in page_source:
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía no está asignada al convenio",
                    'recoverable': False
                }
            elif "ya se encuentra entregada" in page_source:
                return {
                    'success': False,
                    'guia_number': guia_final,
                    'error': "La guía ya se encuentra entregada", 
                    'recoverable': True
                }
            
            # ✅ VERIFICAR ERRORES DE VALIDACIÓN
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
            return {
                'success': False,
                'guia_number': guia_final,
                'error': f"Error en procesamiento: {str(e)}",
                'recoverable': False,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def process_shipment_with_retry(self, guia_data):
        """Procesar guía con reintentos inteligentes"""
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔄 Intento {attempt + 1}/{self.max_retries + 1} para guía [CONFIDENCIAL]")
                
                result = self._process_single_shipment_with_timeout(guia_data)
                
                # ✅ NO REINTENTAR GUÍAS YA ENTREGADAS O NO ASIGNADAS
                if result['success']:
                    return result
                elif result.get('recoverable', False):
                    logger.info("🔄 Error recuperable, continuando con siguiente guía")
                    return result
                elif "no está asignada" in result.get('error', ''):
                    logger.info("🚫 Guía no asignada, no se reintenta")
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