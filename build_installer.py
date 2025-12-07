# build_installer.py - VERSIÓN MEJORADA Y COMPLETA (SIN REPORTLAB)
import os
import shutil
import subprocess
import sys
import platform
import tempfile
import urllib.request
import zipfile
from pathlib import Path

def check_prerequisites():
    """Verificar prerequisitos del sistema"""
    print("🔍 Verificando prerequisitos del sistema...")
    
    # Verificar sistema operativo
    if platform.system() != "Windows":
        print("❌ Este instalador solo funciona en Windows")
        return False
    
    # Verificar Python
    python_version = platform.python_version()
    print(f"✅ Python {python_version} detectado")
    
    # Verificar permisos de administrador (recomendado)
    try:
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            print("✅ Ejecutando con permisos de administrador")
        else:
            print("⚠️  Ejecutando sin permisos de administrador (puede afectar la instalación)")
    except:
        pass
    
    return True

def install_dependencies():
    """Instalar todas las dependencias necesarias (SIN REPORTLAB)"""
    print("📦 Instalando dependencias de Python...")
    
    dependencies = [
        'selenium>=4.15.0',
        'pandas>=2.0.0', 
        'PyQt5>=5.15.0',
        'python-dotenv>=1.0.0',
        'openpyxl>=3.1.0',
        'chromedriver-autoinstaller>=0.4.0',
        'pyinstaller>=5.0.0',
        'requests>=2.31.0'
    ]
    
    for dep in dependencies:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
            print(f"✅ {dep.split('>=')[0]} instalado")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando {dep}: {e}")
            return False
    
    return True

def check_chrome_installed():
    """Verificar si Chrome está instalado - MEJORADO"""
    print("🔍 Verificando Google Chrome...")
    
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            try:
                # Obtener versión de Chrome
                result = subprocess.run([path, '--version'], capture_output=True, text=True)
                version = result.stdout.strip()
                print(f"✅ {version} detectado")
                return True
            except:
                print(f"✅ Chrome detectado en: {path}")
                return True
    
    print("❌ Google Chrome no encontrado")
    print("📥 Descargando Chrome...")
    return download_chrome_installer()

def download_chrome_installer():
    """Descargar instalador de Chrome como respaldo"""
    try:
        chrome_url = "https://dl.google.com/tag/s/appguid%3D%7B8A69D345-D564-463C-AFF1-A69D9E530F96%7D%26iid%3D%7B806F36C0-CB54-4A84-A3F3-0CF8A86517E0%7D%26lang%3Des%26browser%3D4%26usagestats%3D1%26appname%3DGoogle%2520Chrome%26needsadmin%3Dprefers%26ap%3Dx64-stable-statsdef_1%26installdataindex%3Dempty/chrome/install/ChromeStandaloneSetup64.exe"
        
        temp_dir = tempfile.gettempdir()
        chrome_installer = os.path.join(temp_dir, "ChromeStandaloneSetup64.exe")
        
        print("📥 Descargando Chrome...")
        urllib.request.urlretrieve(chrome_url, chrome_installer)
        print(f"✅ Chrome descargado: {chrome_installer}")
        
        # Preguntar si instalar Chrome
        response = input("¿Quieres instalar Chrome ahora? (s/n): ").lower()
        if response == 's':
            print("🔄 Instalando Chrome...")
            subprocess.run([chrome_installer], check=True)
            print("✅ Chrome instalado exitosamente")
            return True
        else:
            print("⚠️  El usuario debe instalar Chrome manualmente")
            return False
            
    except Exception as e:
        print(f"❌ Error descargando Chrome: {e}")
        return False

def install_chromedriver():
    """Instalar ChromeDriver automáticamente - MEJORADO"""
    print("🔧 Configurando ChromeDriver...")
    try:
        import chromedriver_autoinstaller
        
        # Forzar la instalación de la versión correcta
        chromedriver_path = chromedriver_autoinstaller.install()
        
        if chromedriver_path:
            print(f"✅ ChromeDriver instalado en: {chromedriver_path}")
            
            # Verificar que ChromeDriver funciona
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                
                driver = webdriver.Chrome(options=options)
                driver.quit()
                print("✅ ChromeDriver verificado correctamente")
                
            except Exception as e:
                print(f"⚠️  ChromeDriver instalado pero no funciona: {e}")
                print("🔧 Intentando reinstalación...")
                chromedriver_autoinstaller.install(force=True)
                
            return True
        else:
            print("❌ No se pudo instalar ChromeDriver")
            return False
            
    except Exception as e:
        print(f"❌ Error instalando ChromeDriver: {e}")
        return False

def clean_build_dirs():
    """Limpiar directorios de build anteriores - MEJORADO"""
    print("🧹 Limpiando builds anteriores...")
    
    dirs_to_remove = ['build', 'dist', 'AMPMAuto_Installer', '__pycache__']
    files_to_remove = ['AMPMAuto.spec', 'AMPMAuto_Installer.iss']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"✅ Directorio {dir_name} eliminado")
            except Exception as e:
                print(f"⚠️  No se pudo eliminar {dir_name}: {e}")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
                print(f"✅ Archivo {file_name} eliminado")
            except Exception as e:
                print(f"⚠️  No se pudo eliminar {file_name}: {e}")
    
    # Limpiar caché de Python
    for root, dirs, files in os.walk('.'):
        for dir in dirs:
            if dir == '__pycache__':
                cache_dir = os.path.join(root, dir)
                try:
                    shutil.rmtree(cache_dir)
                except:
                    pass

def create_spec_file():
    """Crear archivo .spec para PyInstaller - MEJORADO (SIN REPORTLAB)"""
    print("📝 Creando archivo de configuración PyInstaller...")
    
    spec_content = '''# AMPMAuto.spec - GENERADO AUTOMÁTICAMENTE
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('utils/*.py', 'utils'),
        ('utils/*.py', 'utils'),
        ('*.env', '.'),
        ('requirements.txt', '.'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'selenium', 'PyQt5', 'pandas', 'openpyxl',
        'dotenv', 'chromedriver_autoinstaller',
        'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.period',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'reportlab'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AMPMAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)
'''
    
    with open('AMPMAuto.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("✅ Archivo AMPMAuto.spec creado")

def build_with_pyinstaller():
    """Compilar con PyInstaller - MÉTODO DIRECTO Y CONFIABLE"""
    print("🔨 Compilando aplicación con PyInstaller...")
    
    try:
        # Comando directo sin archivo .spec
        cmd = [
            'pyinstaller',
            'main.py',
            '--onefile',
            '--windowed',
            '--name', 'AMPMAuto',
            '--add-data', 'utils;utils',
            '--add-data', '.env;.' if os.path.exists('.env') else None,
            '--add-data', '.env.example;.' if os.path.exists('.env.example') else None,
            '--add-data', 'requirements.txt;.',
            '--hidden-import', 'PyQt5',
            '--hidden-import', 'selenium',
            '--hidden-import', 'pandas',
            '--hidden-import', 'chromedriver_autoinstaller',
            '--hidden-import', 'openpyxl',
            '--hidden-import', 'python-dotenv',
            '--hidden-import', 'sqlite3',
            '--clean',
            '--noconfirm'
        ]
        
        # Filtrar elementos None
        cmd = [arg for arg in cmd if arg is not None]
        
        # Agregar icono si existe
        if os.path.exists('icon.ico'):
            cmd.extend(['--icon', 'icon.ico'])
        
        print(f"Ejecutando: {' '.join(cmd)}")
        print("⏳ Esto puede tomar varios minutos...")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        
        # Mostrar las últimas líneas del output
        if result.stdout:
            lines = result.stdout.split('\n')
            print("📋 Últimas líneas de PyInstaller:")
            for line in lines[-15:]:
                if line.strip() and 'INFO' in line:
                    print(f"   {line}")
        
        # Verificar que el ejecutable se creó
        if os.path.exists('dist/AMPMAuto.exe'):
            exe_size = os.path.getsize('dist/AMPMAuto.exe') / (1024 * 1024)  # MB
            print(f"✅ Ejecutable creado exitosamente: {exe_size:.1f} MB")
            return True
        else:
            print("❌ No se pudo crear el ejecutable")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en PyInstaller (código {e.returncode}):")
        # Mostrar errores específicos
        error_lines = e.stderr.split('\n')
        for line in error_lines:
            if 'ERROR' in line or 'error' in line.lower():
                print(f"   🔴 {line}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def create_installer_script():
    """Crear script de Inno Setup - MEJORADO"""
    print("📝 Creando script de instalador...")
    
    iss_content = f'''; AMPMAuto_Installer.iss - GENERADO AUTOMÁTICAMENTE
#define MyAppName "AMPMAuto"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AMPMAuto Team"
#define MyAppURL "https://github.com/tuusuario/ampmauto"
#define MyAppExeName "AMPMAuto.exe"
#define MyAppAssocName "AMPMAuto Application"
#define MyAppAssocExt ".exe"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
ChangesAssociations=yes
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputDir=AMPMAuto_Installer
OutputBaseFilename=AMPMAuto_Setup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{{cm:CreateQuickLaunchIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
Source: "dist\\AMPMAuto.exe"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "*.env"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "*.txt"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "*.md"; DestDir: "{{app}}"; Flags: ignoreversion
; Crear directorios necesarios
Source: "reports\\*"; DestDir: "{{app}}\\reports"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "logs\\*"; DestDir: "{{app}}\\logs"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{group}}\\{{cm:UninstallProgram,{{#MyAppName}}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon
Name: "{{userappdata}}\\Microsoft\\Internet Explorer\\Quick Launch\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: quicklaunchicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKA; Subkey: "Software\\Classes\\{{#MyAppAssocExt}}\\OpenWithProgids"; ValueType: string; ValueName: "{{#MyAppAssocKey}}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\\Classes\\{{#MyAppAssocKey}}"; ValueType: string; ValueName: ""; ValueData: "{{#MyAppAssocName}}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\\Classes\\{{#MyAppAssocKey}}\\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{{app}}\\{{#MyAppExeName}},0"
Root: HKA; Subkey: "Software\\Classes\\{{#MyAppAssocKey}}\\shell\\open\\command"; ValueType: string; ValueName: ""; ValueData: """{{app}}\\{{#MyAppExeName}}"" ""%1"""

[Code]
function InitializeSetup(): Boolean;
var
  ChromePath: string;
  ResultCode: Integer;
begin
  Result := True;
  
  // Verificar si Chrome está instalado
  if not RegKeyExists(HKLM, 'SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\App Paths\\\\chrome.exe') then
  begin
    if MsgBox('Google Chrome no está detectado en el sistema. AMPMAuto requiere Chrome para funcionar correctamente.' + #13#10 + #13#10 +
              '¿Desea continuar con la instalación? Puede instalar Chrome después.', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Crear archivo .env de ejemplo si no existe
    if not FileExists(ExpandConstant('{{app}}\\.env')) then
    begin
      SaveStringToFile(ExpandConstant('{{app}}\\.env'),
        '# Configuración AMPMAuto' + #13#10 +
        'AMPM_USERNAME=tu_usuario' + #13#10 +
        'AMPM_PASSWORD=tu_contraseña' + #13#10 +
        'HEADLESS_MODE=True' + #13#10 +
        'TIMEOUT=30' + #13#10 +
        'MAX_RETRIES=3' + #13#10, False);
    end;
  end;
end;
'''
    
    with open('AMPMAuto_Installer.iss', 'w', encoding='utf-8') as f:
        f.write(iss_content)
    print("✅ Script AMPMAuto_Installer.iss creado")

def build_installer():
    """Construir el instalador final - MEJORADO"""
    print("🏗️ Construyendo instalador con Inno Setup...")
    
    try:
        # Buscar Inno Setup en ubicaciones comunes
        inno_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
        ]
        
        iscc_path = None
        for path in inno_paths:
            if os.path.exists(path):
                iscc_path = path
                break
        
        if not iscc_path:
            print("❌ Inno Setup no encontrado")
            print("📥 Descarga Inno Setup desde: https://jrsoftware.org/isdl.php")
            return False
        
        # Compilar el instalador
        result = subprocess.run([iscc_path, 'AMPMAuto_Installer.iss'], 
                              check=True, capture_output=True, text=True)
        
        # Verificar que el instalador se creó
        installer_path = 'AMPMAuto_Installer/AMPMAuto_Setup.exe'
        if os.path.exists(installer_path):
            installer_size = os.path.getsize(installer_path) / (1024 * 1024)  # MB
            print(f"✅ Instalador creado: {installer_path} ({installer_size:.1f} MB)")
            return True
        else:
            print("❌ No se pudo crear el instalador")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en Inno Setup: {e}")
        if e.stderr:
            print(f"Detalles: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def create_additional_files():
    """Crear archivos adicionales necesarios"""
    print("📄 Creando archivos adicionales...")
    
    # Crear LICENSE.txt si no existe
    if not os.path.exists('LICENSE.txt'):
        with open('LICENSE.txt', 'w', encoding='utf-8') as f:
            f.write('''LICENCIA DE AMPMAUTO

Copyright (c) 2024 AMPMAuto Team

Se concede permiso para usar, copiar, modificar y distribuir este software...
''')
        print("✅ LICENSE.txt creado")
    
    # Crear .env.example si no existe
    if not os.path.exists('.env.example'):
        with open('.env.example', 'w', encoding='utf-8') as f:
            f.write('''# Configuración AMPMAuto
AMPM_USERNAME=tu_usuario
AMPM_PASSWORD=tu_contraseña
HEADLESS_MODE=True
TIMEOUT=30
MAX_RETRIES=3
GENERATE_EXCEL_REPORTS=True
''')
        print("✅ .env.example creado")
    
    # Crear directorios necesarios
    for dir_name in ['reports', 'logs']:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✅ Directorio {dir_name} creado")

def verify_final_installation():
    """Verificar la instalación final"""
    print("🔍 Verificando instalación final...")
    
    checks = [
        ('dist/AMPMAuto.exe', 'Ejecutable principal'),
        ('AMPMAuto_Installer/AMPMAuto_Setup.exe', 'Instalador'),
        ('LICENSE.txt', 'Licencia'),
    ]
    
    all_ok = True
    for file_path, description in checks:
        if os.path.exists(file_path):
            print(f"✅ {description}: OK")
        else:
            print(f"❌ {description}: FALTANTE")
            all_ok = False
    
    return all_ok

def main():
    """Función principal"""
    print("🚀 INICIANDO CONSTRUCCIÓN DE INSTALADOR AMPMAUTO")
    print("=" * 60)
    
    try:
        # 1. Verificar prerequisitos
        if not check_prerequisites():
            return 1
        
        # 2. Instalar dependencias (SIN REPORTLAB)
        if not install_dependencies():
            print("❌ Error instalando dependencias")
            return 1
        
        # 3. Verificar Chrome
        if not check_chrome_installed():
            print("⚠️  Chrome no está instalado - la aplicación puede no funcionar")
        
        # 4. Instalar ChromeDriver
        if not install_chromedriver():
            print("⚠️  Problemas con ChromeDriver - la aplicación puede no funcionar")
        
        # 5. Limpiar builds anteriores
        clean_build_dirs()
        
        # 6. Crear archivos adicionales
        create_additional_files()
        
        # 7. Crear archivo .spec
        create_spec_file()
        
        # 8. Compilar con PyInstaller
        if not build_with_pyinstaller():
            print("❌ Error en la compilación")
            return 1
        
        # 9. Crear script de instalador
        create_installer_script()
        
        # 10. Construir instalador
        if not build_installer():
            print("❌ Error creando el instalador")
            return 1
        
        # 11. Verificación final
        if verify_final_installation():
            print("\n🎉 ¡INSTALADOR CREADO EXITOSAMENTE!")
            print("=" * 60)
            print("📁 El instalador está en: AMPMAuto_Installer/AMPMAuto_Setup.exe")
            print("\n📋 Próximos pasos:")
            print("   1. Prueba el instalador en una VM limpia")
            print("   2. Distribuye AMPMAuto_Setup.exe a los usuarios")
            print("   3. Los usuarios solo necesitan ejecutar el .exe")
            print("\n⚠️  Recordatorios:")
            print("   - Los usuarios deben tener Chrome instalado")
            print("   - Proporciona el archivo .env con las credenciales")
            print("   - Ofrece soporte para la primera configuración")
            
            return 0
        else:
            print("❌ Problemas en la verificación final")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Proceso cancelado por el usuario")
        return 1
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())