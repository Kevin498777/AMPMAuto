@echo off
chcp 65001 >nul
echo Limpiando compilaciones anteriores...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q AMPMAuto_Installer 2>nul
rmdir /s /q __pycache__ 2>nul

del AMPMAuto.spec 2>nul
del AMPMAuto_Installer.iss 2>nul

echo Creando estructura necesaria...
mkdir reports 2>nul
mkdir logs 2>nul
echo dummy > reports\dummy.txt
echo dummy > logs\dummy.txt

if not exist LICENSE.txt (
    echo Licencia AMPMAuto > LICENSE.txt
    echo Copyright (c) 2024 >> LICENSE.txt
    echo Desarrollado por: Kevin Brian Ibarra Pineda ISIC >> LICENSE.txt
)

echo Ejecutando build limpio...
python build_installer.py

pause