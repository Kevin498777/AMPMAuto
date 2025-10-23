# report_generator.py - VERSIÓN MEJORADA Y OPTIMIZADA
import os
import pandas as pd
from datetime import datetime
import sys
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def get_app_data_path():
    """Obtener ruta en AppData/Local para archivos de usuario - MEJORADO"""
    try:
        if os.name == 'nt':  # Windows
            app_data = os.getenv('LOCALAPPDATA')
            if app_data:
                app_path = os.path.join(app_data, 'AMPMAuto')
                os.makedirs(app_path, exist_ok=True)
                return app_path
        # Fallback para Linux/Mac y casos de error
        fallback_path = os.path.join(os.path.expanduser('~'), '.ampmauto')
        os.makedirs(fallback_path, exist_ok=True)
        return fallback_path
    except Exception as e:
        logger.warning(f"No se pudo crear directorio en AppData: {e}")
        # Último fallback: directorio actual
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        reports_dir = os.path.join(current_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        return reports_dir

class ReportGenerator:
    """Generador de reportes para AMPMAuto - VERSIÓN MEJORADA"""
    
    def __init__(self, output_dir: Optional[str] = None):
        # Usar carpeta con permisos de escritura garantizados
        if output_dir is None:
            output_dir = os.path.join(get_app_data_path(), "reports")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self._check_dependencies()
        logger.info(f"📁 Reportes se guardarán en: {self.output_dir}")
    
    def _check_dependencies(self):
        """Verificar dependencias disponibles"""
        self.reportlab_available = False
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate
            self.reportlab_available = True
            logger.info("✅ ReportLab disponible para generación de PDF")
        except ImportError:
            logger.warning("⚠️ ReportLab no disponible - Solo se generarán reportes Excel")
    
    def generate_report(self, report_data: Optional[Dict] = None) -> Tuple[Optional[str], Optional[str]]:
        """Genera un reporte en PDF y Excel con los resultados de la automatización"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Validar datos de entrada
            if report_data is None:
                logger.warning("No se proporcionaron datos, generando reporte de ejemplo")
                report_data = self._get_sample_data()
            elif not self._validate_report_data(report_data):
                logger.error("Datos de reporte inválidos")
                return None, None
            
            # Generar reporte Excel (siempre disponible)
            excel_path = os.path.join(self.output_dir, f"reporte_ampm_{timestamp}.xlsx")
            success = self._generate_excel_report(excel_path, report_data)
            
            if not success:
                logger.error("Falló la generación del reporte Excel")
                return None, None
            
            # Generar PDF si está disponible
            pdf_path = None
            if self.reportlab_available:
                try:
                    pdf_path = os.path.join(self.output_dir, f"reporte_ampm_{timestamp}.pdf")
                    self._generate_pdf_report(pdf_path, report_data)
                    logger.info(f"📊 Reportes generados: {pdf_path} y {excel_path}")
                except Exception as e:
                    logger.error(f"Error generando PDF: {e}")
                    pdf_path = None
            else:
                logger.info(f"📊 Reporte Excel generado: {excel_path}")
            
            return excel_path, pdf_path
            
        except Exception as e:
            logger.error(f"❌ Error crítico al generar reporte: {str(e)}")
            return None, None
    
    def _validate_report_data(self, report_data: Dict) -> bool:
        """Validar estructura de datos del reporte"""
        required_fields = ['total', 'success', 'errors', 'timestamp', 'results']
        for field in required_fields:
            if field not in report_data:
                logger.error(f"Campo requerido faltante: {field}")
                return False
        return True
    
    def _get_sample_data(self) -> Dict:
        """Generar datos de ejemplo para testing"""
        return {
            'total': 15,
            'success': 12,
            'errors': 3,
            'recovered': 1,
            'timestamp': datetime.now(),
            'excel_file': 'archivo_ejemplo.xlsx',
            'results': [
                {'success': True, 'guia_number': '45123456789', 'message': 'Procesado exitosamente', 'processing_time': 12.5},
                {'success': True, 'guia_number': '45123456790', 'message': 'Procesado exitosamente', 'processing_time': 11.2},
                {'success': False, 'guia_number': '45123456791', 'error': 'Guía ya entregada', 'recoverable': True},
                {'success': False, 'guia_number': '45123456792', 'error': 'Error de conexión', 'recoverable': False},
            ]
        }
    
    def _generate_pdf_report(self, file_path: str, report_data: Dict):
        """Genera un reporte en PDF con formato profesional"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            
            doc = SimpleDocTemplate(file_path, pagesize=letter, topMargin=0.5*inch)
            styles = getSampleStyleSheet()
            story = []
            
            # Título principal
            title_style = styles['Title']
            title_style.alignment = 1  # Centrado
            title = Paragraph("REPORTE DE AUTOMATIZACIÓN - AMPMAUTO", title_style)
            story.append(title)
            story.append(Spacer(1, 0.2*inch))
            
            # Información general
            normal_style = styles['Normal']
            story.append(Paragraph(f"<b>Fecha de generación:</b> {report_data['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}", normal_style))
            story.append(Paragraph(f"<b>Archivo procesado:</b> {report_data.get('excel_file', 'N/A')}", normal_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Resumen estadístico
            total = report_data['total']
            success = report_data['success']
            errors = report_data['errors']
            recovered = report_data.get('recovered', 0)
            real_errors = errors - recovered
            
            effectiveness = (success / total * 100) if total > 0 else 0
            
            story.append(Paragraph("<b>RESUMEN ESTADÍSTICO:</b>", styles['Heading2']))
            summary_data = [
                ['Total de Guías', str(total)],
                ['Guías Exitosas', f"{success} ({effectiveness:.1f}%)"],
                ['Guías Ya Entregadas', str(recovered)],
                ['Errores Reales', str(real_errors)],
                ['Tasa de Éxito', f"{effectiveness:.1f}%"]
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DEE2E6'))
            ]))
            story.append(summary_table)
            story.append(Spacer(1, 0.2*inch))
            
            # Tabla de resultados detallados
            if report_data['results']:
                story.append(Paragraph("<b>DETALLE DE GUÍAS PROCESADAS:</b>", styles['Heading2']))
                
                # Preparar datos para la tabla
                data = [['Guía', 'Estado', 'Tiempo (s)', 'Mensaje/Error']]
                for result in report_data['results']:
                    guia = result.get('guia_number', 'N/A')
                    
                    if result['success']:
                        estado = "✅ ÉXITO"
                        tiempo = f"{result.get('processing_time', 0):.2f}" if result.get('processing_time') else 'N/A'
                        mensaje = result.get('message', 'Procesado correctamente')
                    else:
                        if result.get('recoverable', False):
                            estado = "⚠️ YA ENTREGADA"
                        else:
                            estado = "❌ ERROR"
                        tiempo = 'N/A'
                        mensaje = result.get('error', 'Error desconocido')
                    
                    data.append([guia, estado, tiempo, mensaje])
                
                # Crear tabla
                table = Table(data, colWidths=[1.2*inch, 1*inch, 0.8*inch, 3*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343A40')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ADB5BD')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
                ]))
                story.append(table)
            
            # Pie de página
            story.append(Spacer(1, 0.3*inch))
            footer = Paragraph(
                f"<i>Generado automáticamente por AMPMAuto v1.3.2 - {datetime.now().strftime('%d/%m/%Y %H:%M')}</i>", 
                styles['Italic']
            )
            story.append(footer)
            
            doc.build(story)
            logger.info(f"✅ Reporte PDF generado: {file_path}")
            
        except Exception as e:
            logger.error(f"❌ Error al generar PDF: {str(e)}")
            raise
    
    def _generate_excel_report(self, file_path: str, report_data: Dict) -> bool:
        """Genera un reporte en Excel con formato profesional"""
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Hoja de resumen
                summary_data = {
                    'Métrica': [
                        'Fecha de Generación',
                        'Archivo Procesado', 
                        'Total de Guías',
                        'Guías Exitosas',
                        'Guías Ya Entregadas',
                        'Errores Reales',
                        'Tasa de Éxito'
                    ],
                    'Valor': [
                        report_data['timestamp'].strftime('%d/%m/%Y %H:%M:%S'),
                        report_data.get('excel_file', 'N/A'),
                        report_data['total'],
                        report_data['success'],
                        report_data.get('recovered', 0),
                        report_data['errors'] - report_data.get('recovered', 0),
                        f"{(report_data['success'] / report_data['total'] * 100):.1f}%" if report_data['total'] > 0 else "0%"
                    ]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Resumen', index=False)
                
                # Hoja de resultados detallados
                if report_data['results']:
                    detailed_data = []
                    for result in report_data['results']:
                        row = {
                            'Guía': result.get('guia_number', 'N/A'),
                            'Estado': 'ÉXITO' if result['success'] else ('YA ENTREGADA' if result.get('recoverable') else 'ERROR'),
                            'Tiempo_Procesamiento_Segundos': result.get('processing_time', 'N/A'),
                            'Mensaje_Error': result.get('message', result.get('error', 'N/A')),
                            'Timestamp': result.get('timestamp', 'N/A'),
                            'Recuperable': 'Sí' if result.get('recoverable') else 'No'
                        }
                        detailed_data.append(row)
                    
                    df_detailed = pd.DataFrame(detailed_data)
                    df_detailed.to_excel(writer, sheet_name='Detalle_Guías', index=False)
                
                # Hoja de estadísticas
                stats_data = {
                    'Estadística': [
                        'Tiempo Total Estimado (segundos)',
                        'Tiempo Promedio por Guía (segundos)',
                        'Guías por Minuto',
                        'Eficiencia del Proceso'
                    ],
                    'Valor': [
                        sum(r.get('processing_time', 0) for r in report_data['results'] if r.get('processing_time')),
                        self._calculate_avg_time(report_data['results']),
                        self._calculate_guides_per_minute(report_data['results']),
                        f"{(report_data['success'] / report_data['total'] * 100):.1f}%" if report_data['total'] > 0 else "0%"
                    ]
                }
                df_stats = pd.DataFrame(stats_data)
                df_stats.to_excel(writer, sheet_name='Estadísticas', index=False)
                
                # Obtener workbook para formateo
                workbook = writer.book
                
                # Formatear hoja de resumen
                if 'Resumen' in workbook.sheetnames:
                    worksheet = workbook['Resumen']
                    worksheet.column_dimensions['A'].width = 25
                    worksheet.column_dimensions['B'].width = 30
                
                # Formatear hoja de detalle
                if 'Detalle_Guías' in workbook.sheetnames:
                    worksheet = workbook['Detalle_Guías']
                    worksheet.column_dimensions['A'].width = 15
                    worksheet.column_dimensions['B'].width = 12
                    worksheet.column_dimensions['C'].width = 10
                    worksheet.column_dimensions['D'].width = 40
                    worksheet.column_dimensions['E'].width = 20
                    worksheet.column_dimensions['F'].width = 12
            
            logger.info(f"✅ Reporte Excel generado: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al generar Excel: {str(e)}")
            return False
    
    def _calculate_avg_time(self, results: List[Dict]) -> str:
        """Calcular tiempo promedio de procesamiento"""
        valid_times = [r.get('processing_time', 0) for r in results if r.get('processing_time')]
        if valid_times:
            avg = sum(valid_times) / len(valid_times)
            return f"{avg:.2f}s"
        return "N/A"
    
    def _calculate_guides_per_minute(self, results: List[Dict]) -> str:
        """Calcular guías procesadas por minuto"""
        total_time = sum(r.get('processing_time', 0) for r in results if r.get('processing_time'))
        if total_time > 0:
            gpm = len(results) / (total_time / 60)
            return f"{gpm:.1f}"
        return "N/A"

# Funciones de conveniencia para uso rápido
def generate_quick_report(success_count: int, error_count: int, total_count: int, recovered_count: int = 0) -> Tuple[Optional[str], Optional[str]]:
    """Genera un reporte rápido con datos básicos"""
    generator = ReportGenerator()
    report_data = {
        'total': total_count,
        'success': success_count,
        'errors': error_count,
        'recovered': recovered_count,
        'timestamp': datetime.now(),
        'results': []
    }
    return generator.generate_report(report_data)

def generate_detailed_report(results: List[Dict], excel_file: str = "") -> Tuple[Optional[str], Optional[str]]:
    """Genera un reporte detallado con resultados específicos"""
    generator = ReportGenerator()
    
    success_count = sum(1 for r in results if r.get('success'))
    recovered_count = sum(1 for r in results if r.get('recoverable') and not r.get('success'))
    error_count = len(results) - success_count - recovered_count
    
    report_data = {
        'total': len(results),
        'success': success_count,
        'errors': error_count + recovered_count,  # Total de no-éxitos
        'recovered': recovered_count,
        'timestamp': datetime.now(),
        'excel_file': excel_file,
        'results': results
    }
    
    return generator.generate_report(report_data)

# Ejemplo de uso
if __name__ == "__main__":
    # Configurar logging para prueba
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Generar reporte de ejemplo
    generator = ReportGenerator()
    excel_path, pdf_path = generator.generate_report()
    
    if excel_path:
        print(f"✅ Reporte Excel generado: {excel_path}")
    if pdf_path:
        print(f"✅ Reporte PDF generado: {pdf_path}")