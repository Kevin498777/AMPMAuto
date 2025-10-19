# test_installation.py
try:
    from dotenv import load_dotenv
    print("✅ python-dotenv instalado correctamente")
except ImportError as e:
    print("❌ Error con python-dotenv:", e)

try:
    from PyQt5 import QtWidgets
    print("✅ PyQt5 instalado correctamente")
except ImportError as e:
    print("❌ Error con PyQt5:", e)

try:
    import selenium
    print("✅ Selenium instalado correctamente")
except ImportError as e:
    print("❌ Error con Selenium:", e)

try:
    import pandas
    print("✅ Pandas instalado correctamente")
except ImportError as e:
    print("❌ Error con Pandas:", e)

try:
    import reportlab
    print("✅ ReportLab instalado correctamente")
except ImportError as e:
    print("❌ Error con ReportLab:", e)

print("\n🎯 Si todos muestran ✅, tu aplicación debería funcionar!")