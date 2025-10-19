# report_generator.py
import os
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import logging

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, output_dir="reports"):
        self.output_dir = output_dir
        # Crear directorio si no existe
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_report(self, report_data=None):
        """Genera un reporte en PDF y Excel con los resultados de la automatización"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Si no se proporcionan datos, generamos un ejemplo
            if report_data is None:
                report_data = {
                    'total': 10,
                    'success': 8,
                    'errors': 2,
                    'timestamp': datetime.now(),
                    'results': [
                        {'success': True, 'guia_number': 'GUIA001', 'message': 'Procesado exitosamente'},
                        {'success': True, 'guia_number': 'GUIA002', 'message': 'Procesado exitosamente'},
                        {'success': False, 'guia_number': 'GUIA003', 'error': 'Error de conexión'},
                    ]
                }
            
            # Generar reporte PDF
            pdf_path = os.path.join(self.output_dir, f"reporte_ampm_{timestamp}.pdf")
            self._generate_pdf_report(pdf_path, report_data)
            
            # Generar reporte Excel
            excel_path = os.path.join(self.output_dir, f"reporte_ampm_{timestamp}.xlsx")
            self._generate_excel_report(excel_path, report_data)
            
            logger.info(f"Reportes generados: {pdf_path} y {excel_path}")
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error al generar reporte: {str(e)}")
            return None
    
    def _generate_pdf_report(self, file_path, report_data):
        """Genera un reporte en PDF"""
        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Título
            title = Paragraph("Reporte de Automatización - AMPMAuto", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # Información general
            story.append(Paragraph(f"Fecha: {report_data['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
            story.append(Paragraph(f"Total de guías: {report_data['total']}", styles['Normal']))
            story.append(Paragraph(f"Guías exitosas: {report_data['success']}", styles['Normal']))
            story.append(Paragraph(f"Guías con error: {report_data['errors']}", styles['Normal']))
            story.append(Spacer(1, 12))
            
            # Tabla de resultados
            if report_data['results']:
                data = [['Guía', 'Estado', 'Mensaje']]
                for result in report_data['results']:
                    estado = "Éxito" if result['success'] else "Error"
                    mensaje = result.get('message', result.get('error', 'N/A'))
                    data.append([result.get('guia_number', 'N/A'), estado, mensaje])
                
                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(table)
            
            doc.build(story)
            logger.info(f"Reporte PDF generado: {file_path}")
            
        except Exception as e:
            logger.error(f"Error al generar PDF: {str(e)}")
            raise
    
    def _generate_excel_report(self, file_path, report_data):
        """Genera un reporte en Excel"""
        try:
            if report_data['results']:
                df = pd.DataFrame(report_data['results'])
                # Renombrar columnas para mejor presentación
                df['Estado'] = df['success'].apply(lambda x: 'Éxito' if x else 'Error')
                df['Guía'] = df['guia_number']
                df['Mensaje'] = df.apply(lambda row: row.get('message', row.get('error', 'N/A')), axis=1)
                df = df[['Guía', 'Estado', 'Mensaje']]
            else:
                df = pd.DataFrame(columns=['Guía', 'Estado', 'Mensaje'])
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Resultados', index=False)
                
                # Formatear la hoja de resumen
                workbook = writer.book
                worksheet = workbook.create_sheet("Resumen", 0)
                
                worksheet['A1'] = 'Resumen de Automatización - AMPMAuto'
                worksheet['A2'] = f"Fecha: {report_data['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}"
                worksheet['A3'] = f"Total de guías: {report_data['total']}"
                worksheet['A4'] = f"Guías exitosas: {report_data['success']}"
                worksheet['A5'] = f"Guías con error: {report_data['errors']}"
            
            logger.info(f"Reporte Excel generado: {file_path}")
            
        except Exception as e:
            logger.error(f"Error al generar Excel: {str(e)}")
            raise

# Función de conveniencia para uso rápido
def generate_quick_report(success_count, error_count, total_count):
    """Genera un reporte rápido con datos básicos"""
    generator = ReportGenerator()
    report_data = {
        'total': total_count,
        'success': success_count,
        'errors': error_count,
        'timestamp': datetime.now(),
        'results': []
    }
    return generator.generate_report(report_data)