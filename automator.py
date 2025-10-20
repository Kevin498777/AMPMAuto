# automator_mejorado.py - VERSIÓN SIMPLIFICADA
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import time
import logging
import os
from utils.config import ConfigManager

logger = logging.getLogger(__name__)

class AMPMAutomatorRobusto:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.config = ConfigManager()
        self.is_logged_in = False
        self.max_processing_time = 30
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
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, self.config.timeout)
            logger.info("✅ Navegador Chrome inicializado correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar el navegador: {str(e)}")
            raise
    
    def wait_for_modal_to_close(self, timeout=10):
        """Esperar a que el modal de error desaparezca"""
        try:
            logger.info("⏳ Esperando a que cierre el modal de error...")
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "ui-dialog"))
            )
            logger.info("✅ Modal de error cerrado")
            return True
        except TimeoutException:
            logger.warning("⚠️ Modal no se cerró automáticamente, intentando cerrar manualmente...")
            try:
                close_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@class, 'ui-dialog-titlebar-close')]")
                for button in close_buttons:
                    if button.is_displayed():
                        self.driver.execute_script("arguments[0].click();", button)
                        logger.info("✅ Modal cerrado manualmente")
                        return True
            except:
                pass
            return False
    
    def handle_errors(self):
        """Manejar errores de validación en la página"""
        try:
            # Verificar errores de campo
            field_errors = self.driver.find_elements(By.CLASS_NAME, "field-validation-error")
            visible_field_errors = [elem for elem in field_errors if elem.is_displayed() and elem.text.strip()]
            
            if visible_field_errors:
                error_text = visible_field_errors[0].text
                logger.error(f"❌ Error de validación: {error_text}")
                return error_text
            
            # Verificar modales de error
            modal_errors = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'no es válida') or contains(text(), 'error') or contains(text(), 'inválida') or contains(text(), 'repetida') or contains(text(), 'duplicada')]")
            visible_modal_errors = [elem for elem in modal_errors if elem.is_displayed()]
            
            if visible_modal_errors:
                error_text = visible_modal_errors[0].text
                logger.error(f"❌ Error en modal: {error_text}")
                self.wait_for_modal_to_close()
                return error_text
            
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
        """Procesa una guía individual con timeout controlado"""
        import time
        start_time = time.time()
        
        guia_number = guia_data.get('numero_guia', 'N/A')
        logger.info(f"📦 Procesando guía: [CONFIDENCIAL]")
        
        # Verificar timeout periódicamente
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
        
        # Extraer solo números si la guía tiene formato mixto
        if not str(guia_number).isdigit():
            import re
            numeros = re.findall(r'\d+', str(guia_number))
            if numeros:
                guia_number = numeros[0]
                logger.info(f"🔢 Guía convertida: [CONFIDENCIAL] → {guia_number}")
        
        guia_field = self.wait.until(EC.presence_of_element_located((By.ID, "GuiaId")))
        
        guia_field.clear()
        guia_field.send_keys(str(guia_number))
        
        guia_field.send_keys(Keys.ENTER)
        logger.info(f"✅ Guía [CONFIDENCIAL] ingresada, esperando detalles...")
        
        check_timeout()
        time.sleep(4)
        check_timeout()
        
        error_message = self.handle_errors()
        if error_message:
            return {
                'success': False,
                'guia_number': '[CONFIDENCIAL]',
                'error': f"Error en guía: {error_message}"
            }
        
        check_timeout()
        
        entregar_button = self.wait.until(
            EC.element_to_be_clickable((By.ID, "btnEntregar"))
        )
        self.driver.execute_script("arguments[0].click();", entregar_button)
        logger.info(f"✅ Botón Entregar presionado para guía [CONFIDENCIAL]")
        
        check_timeout()
        time.sleep(3)
        check_timeout()
        
        error_message = self.handle_errors()
        if error_message:
            return {
                'success': False,
                'guia_number': '[CONFIDENCIAL]',
                'error': f"Error al entregar: {error_message}"
            }
        
        logger.info(f"✅ Guía [CONFIDENCIAL] procesada exitosamente")
        
        try:
            nuevo_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "btnNuevo"))
            )
            self.driver.execute_script("arguments[0].click();", nuevo_button)
            logger.info("✅ Campos limpiados con botón Nuevo")
            time.sleep(1)
        except:
            logger.info("ℹ️ No se pudo hacer clic en Nuevo, continuando...")
        
        processing_time = time.time() - start_time
        logger.info(f"⏱️ Tiempo de procesamiento: {processing_time:.2f} segundos")
        
        return {
            'success': True,
            'guia_number': '[CONFIDENCIAL]',
            'message': 'Guía registrada exitosamente en AMPM',
            'processing_time': processing_time,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def process_shipment(self, guia_data):
        """Procesar una guía individual con manejo robusto de errores"""
        try:
            return self._process_single_shipment_with_timeout(guia_data)
            
        except TimeoutException as e:
            error_msg = f"⏰ TIMEOUT - Guía [CONFIDENCIAL] tardó demasiado: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'guia_number': '[CONFIDENCIAL]',
                'error': error_msg,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            error_msg = f"🚨 ERROR CRÍTICO - Guía [CONFIDENCIAL] falló: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'guia_number': '[CONFIDENCIAL]',
                'error': error_msg,
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

# FUNCIÓN DE PRUEBA SIMPLIFICADA - USA TU ARCHIVO EXISTENTE
def test_ampm_robusto():
    """Función para probar con manejo robusto de errores usando TU archivo"""
    print("🚀 PROBANDO SISTEMA CON MANEJO ROBUSTO DE ERRORES")
    print("=" * 60)
    
    # USA TU ARCHIVO EXISTENTE
    excel_file_path = r"D:\Proyecto\Pruebas\prueba1.xlsx"
    
    if not os.path.exists(excel_file_path):
        print(f"❌ Archivo no encontrado: {excel_file_path}")
        print("💡 Sugerencia: Usa tu archivo prueba1.xlsx existente")
        return False
    
    try:
        import pandas as pd
        df = pd.read_excel(excel_file_path)
        
        if len(df) == 0:
            print("❌ El Excel está vacío")
            return False
            
        total_guias = len(df)
        
        print(f"✅ Usando tu archivo: {os.path.basename(excel_file_path)}")
        print(f"📦 Total de guías: {total_guias}")
        print(f"🛡️  Sistema configurado para CONTINUAR después de errores")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return False
    
    automator = AMPMAutomatorRobusto(headless=False)
    try:
        success_count = 0
        error_count = 0
        results = []
        
        for index, row in df.iterrows():
            guia_data = row.to_dict()
            
            print(f"\n🔍 PROCESANDO GUÍA {index + 1}/{total_guias}")
            
            result = automator.process_shipment(guia_data)
            results.append(result)
            
            if result['success']:
                success_count += 1
                print(f"   ✅ ÉXITO: Procesada correctamente")
                print(f"   ⏱️  Tiempo: {result.get('processing_time', 'N/A')}s")
            else:
                error_count += 1
                print(f"   ❌ ERROR: {result.get('error', 'Error desconocido')}")
                print(f"   🔄 CONTINUANDO con siguiente guía...")
            
            # Pequeña pausa entre guías
            time.sleep(2)
        
        print("\n" + "=" * 60)
        print("🎯 RESUMEN FINAL:")
        print(f"   ✅ Guías exitosas: {success_count}")
        print(f"   ❌ Guías con error: {error_count}") 
        print(f"   📊 Total procesadas: {total_guias}")
        
        # Mostrar solo si hay errores
        if error_count > 0:
            print(f"\n⚠️  DETALLE DE ERRORES (EL SISTEMA CONTINUÓ):")
            for i, result in enumerate(results):
                if not result['success']:
                    print(f"   Guía {i+1}: {result.get('error', 'N/A')}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ ERROR GLOBAL en prueba: {str(e)}")
        return False
    finally:
        automator.close()

if __name__ == "__main__":
    # Ejecutar prueba robusta con TU archivo
    test_ampm_robusto()