# generate_test_excel.py
import pandas as pd
import random
from datetime import datetime

def generate_test_excel():
    """Genera un archivo Excel con guías de prueba"""
    
    # Lista de guías proporcionadas
    guias = [
        "5713611256", "45705084408", "45713769990", "45704262443", "AMPM8003579",
        "AMPM8009534", "958494950016", "955337230010", "45709834061", "954478260019",
        "45704880850", "45713591400", "45702592202", "45709736037", "45709116975",
        "45709736031", "45708106099", "45686654524", "45686165540", "45713701162",
        "45712092109", '{"ID":"45706599155","t":"lm"}', "45690641525", '{"id":"45707569377","t":"lm"}',
        "45701442857", '{"ID":"45691972185","t":"lm"}', '{"ID":"45697360575","t":"lm"}',
        "45702688936", "45712067607", "45710301322", "45710049483", "45710271642",
        "45676645942", "", "", "", "", "", "", "", "", "45708345049",  # Nota: hay espacios vacíos
        '{"ID":"45710028228","t":"lm"}', "45702868348", "45699200973", '{"ID":"45699893414","t":"lm"}',
        "45706448119", "45709775915", '{"id":"45710967984","t":"lm"}', "45705258936",
        "45711320060", '{"ID":"45709480808","t":"lm"}', '{"ID":"45713964142","t":"lm"}',
        '{"ID":"45707799545","t":"lm"}', '{"ID":"45712075351","t":"lm"}', '{"ID":"45709731729","t":"lm"}',
        '{"ID":"45714000466","t":"lm"}', "45702600466", "45705493502", '{"ID":"45710092436","t":"lm"}',
        "45707953882", "45710496827", '{"ID":"45709712295","t":"lm"}', "45711116456",
        "45707954204", "45705259228", "955505890017", "45712693585", "45712538543",
        "956730080010", "5713415303", "45702930388", "45713700753", "45702452529",
        "45708008392", "45702678873", '{"id":"45709840689","t":"lm"}', "45709950145",
        "45711621905", '{"id":"45710496841","t":"lm"}', "45702678857", "45695819459",
        "45696070394", "953494950016", "45697360575", "5703670903", "45708008392",
        "45710496841", "45702452529", '{"id":"45713415303","t":"lm"}', "45702930388",
        '{"id":"45713700753","t":"lm"}', "45709950145", "45702678873", '{"id":"45709840689","t":"lm"}',
        '{"id":"45709712295","t":"lm"}', "45711621905", "45691164730", "45691164730"
    ]
    
    # Nombres de destinatarios para hacerlo más realista
    destinatarios = [
        "Juan Pérez Martínez", "María García López", "Carlos Rodríguez Silva", 
        "Ana Fernández Castro", "Luis Martínez González", "Laura Sánchez Ruiz",
        "Miguel Ángel Díaz", "Elena Ramírez Vargas", "Roberto Navarro Jiménez",
        "Isabel Morales Ortega", "Javier Torres Mendoza", "Carmen Reyes Paredes",
        "David Herrera Rojas", "Patricia Castro León", "José Luis Flores Campos",
        "Sofía Vega Montes", "Francisco Núñez Ríos", "Teresa Medina Salazar",
        "Antonio Guerrero Parra", "Rosa María Delgado", "Manuel Ortiz Fuentes",
        "Lucía Peña Cervantes", "Ricardo Soto Miranda", "Beatriz Cruz Hidalgo",
        "Alberto Mendoza Reyes", "Mónica Acosta Padilla", "Fernando Rivas Pacheco",
        "Silvia Castillo Bravo", "Raúl Vargas Luna", "Cecilia Paredes Santana"
    ]
    
    # Direcciones de ejemplo
    direcciones = [
        "Av. Revolución 123, Col. Centro", "Calle Morelos 456, Col. Moderna",
        "Blvd. López Mateos 789, Col. Industrial", "Privada Hidalgo 321, Col. Juárez",
        "Calzada Independencia 654, Col. Libertad", "Circuito Universidad 987, Col. Estudiantil",
        "Eje Central 147, Col. Obrera", "Periférico Norte 258, Col. Residencial",
        "Anillo Periférico 369, Col. Las Águilas", "Vía López Portillo 741, Col. San Ángel",
        "Av. de los Insurgentes 852, Col. Nápoles", "Paseo de la Reforma 963, Col. Cuauhtémoc",
        "Calzada de Tlalpan 159, Col. Roma", "Av. Constituyentes 753, Col. Del Valle",
        "Eje 5 Sur 486, Col. Portales", "Av. Miguel Ángel 297, Col. Narvarte",
        "Cuitláhuac 618, Col. Normal", "Av. División del Norte 834, Col. Del Carmen",
        "Félix Cuevas 275, Col. Tlacoquemécatl", "Av. Coyoacán 916, Col. Parque San Andrés"
    ]
    
    # Crear DataFrame
    data = []
    for i, guia in enumerate(guias):
        # Si la guía está vacía, la dejamos vacía para probar el manejo de errores
        if guia.strip() == "":
            data.append({
                'numero_guia': '',
                'destinatario': '',
                'direccion': ''
            })
        else:
            data.append({
                'numero_guia': guia,
                'destinatario': random.choice(destinatarios),
                'direccion': random.choice(direcciones)
            })
    
    df = pd.DataFrame(data)
    
    # Nombre del archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"guias_prueba_{timestamp}.xlsx"
    
    # Guardar Excel
    df.to_excel(filename, index=False)
    
    print(f"✅ Archivo Excel generado: {filename}")
    print(f"📊 Total de guías: {len(df)}")
    print(f"📝 Guías vacías: {len(df[df['numero_guia'] == ''])}")
    print(f"🔢 Guías con formato JSON: {len([g for g in guias if 'ID' in str(g) or 'id' in str(g)])}")
    print(f"🚚 Guías AMPM: {len([g for g in guias if 'AMPM' in str(g)])}")
    
    # Mostrar primeras 5 filas
    print("\n📋 Primeras 5 guías:")
    print(df.head())
    
    return filename

if __name__ == "__main__":
    generate_test_excel()