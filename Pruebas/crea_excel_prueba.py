# crea_excel_prueba.py
import pandas as pd

data = {
    'numero_guia': ['GUIA001', 'GUIA002', 'GUIA003', 'GUIA004'],
    'destinatario': ['Juan Pérez', 'María García', 'Carlos López', 'Ana Rodríguez'],
    'direccion': ['Calle 123, Ciudad México', 'Avenida 456, Guadalajara', 'Boulevard 789, Monterrey', 'Privada 321, Puebla'],
    'peso': [1.5, 2.0, 0.5, 3.0],
    'contenido': ['Documentos', 'Ropa', 'Muestras', 'Electrónicos'],
    'telefono': ['5551234567', '5557654321', '5558889999', '5554443333']
}

df = pd.DataFrame(data)
df.to_excel('guias_ejemplo.xlsx', index=False)
print("✅ Archivo guias_ejemplo.xlsx creado exitosamente")