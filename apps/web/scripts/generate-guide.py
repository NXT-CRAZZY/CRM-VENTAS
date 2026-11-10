"""Genera una guia rapida en PDF con capturas del CRM."""

from pathlib import Path

from fpdf import FPDF

OUT_DIR = Path('C:/Users/PC/AppData/Local/Temp/opencode/crm-flow')
PDF_OUT = Path('C:/Users/PC/Downloads/CRM-VENTAS/docs/manual/Guia_Rapida_DSCONT_Ventas.pdf')

PAGES = [
    ('01-login', '1. Inicio de sesion', 'Ingresa con tu correo y contrasena. El admin inicial es admin@dataservice.pe / Admin123!.'),
    ('02-inicio', '2. Dashboard', 'Resumen diario: tareas, prospectos sin contacto, alto interes y accesos rapidos.'),
    ('03-prospectos', '3. Prospectos', 'Lista de personas y empresas. Filtros por estado, busqueda y boton Nuevo prospecto.'),
    ('04-prospecto-detalle', '4. Ficha del prospecto', 'Ver datos de contacto, interacciones, oportunidades y cotizaciones historicas.'),
    ('05-pipeline', '5. Pipeline de ventas', 'Arrastra oportunidades entre etapas: Nuevo, Cotizacion, Negociacion, Cerrado.'),
    ('06-cotizaciones', '6. Cotizaciones', 'Propuestas comerciales con estados: Borrador, Enviada, Aceptada, Rechazada.'),
    ('07-tareas', '7. Tareas', 'Seguimiento de actividades pendientes, vencidas y completadas.'),
    ('08-alertas', '8. Alertas', 'Notificaciones del sistema sobre prospectos que requieren atencion.'),
    ('09-informe-semanal', '9. Informe semanal', 'Reporte consolidado de gestion para enviar a gerencia.'),
    ('10-dashboard-gerencial', '10. Dashboard gerencial', 'Vista de negocio con montos, etapas y prospectos por responsable.'),
    ('11-productos', '11. Productos y servicios', 'Catalogo comercial con precios y unidades de medida.'),
    ('13-configuracion', '12. Configuracion', 'Administra motivos de perdida, estados, tipos de contacto y otros catalogos.'),
]


class GuidePDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font('helvetica', '', 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, 'Guia rapida - DSCONT Ventas CRM', align='L')
        self.cell(0, 8, f'Pagina {self.page_no()}', align='R')
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font('helvetica', '', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'DATA SERVICE - DSCONT Ventas', align='C')


pdf = GuidePDF(orientation='L', unit='mm', format='A4')
pdf.set_auto_page_break(False)
pdf.set_margins(10, 10, 10)

# Portada
pdf.add_page()
pdf.set_font('helvetica', 'B', 28)
pdf.set_text_color(224, 62, 15)
pdf.cell(0, 30, 'DSCONT Ventas CRM', align='C')
pdf.ln(12)
pdf.set_font('helvetica', '', 16)
pdf.set_text_color(36, 37, 40)
pdf.cell(0, 12, 'Guia rapida de uso', align='C')
pdf.ln(30)

pdf.set_font('helvetica', '', 12)
pdf.set_text_color(60, 60, 60)
pdf.multi_cell(0, 8,
    'Este documento resume el flujo basico del CRM comercial: '
    'desde el ingreso al sistema hasta la gestion de prospectos, '
    'oportunidades, cotizaciones, tareas y reportes.', align='C')
pdf.ln(10)

pdf.set_font('helvetica', 'B', 12)
pdf.cell(0, 10, 'Credenciales de prueba', align='C')
pdf.ln(10)
pdf.set_font('helvetica', '', 11)
pdf.cell(0, 8, 'admin@dataservice.pe / Admin123!  (Administrador)', align='C')
pdf.ln(7)
pdf.cell(0, 8, 'gerencia@dataservice.pe / Demo1234  (Gerencia)', align='C')
pdf.ln(7)
pdf.cell(0, 8, 'maria.quispe@dataservice.pe / Demo1234  (Ventas)', align='C')

# Contenido: 2 capturas por pagina
for i in range(0, len(PAGES), 2):
    pdf.add_page()
    left = PAGES[i]
    right = PAGES[i + 1] if i + 1 < len(PAGES) else None

    def draw_block(x, img_name, title, desc):
        pdf.set_xy(x, 18)
        pdf.set_font('helvetica', 'B', 13)
        pdf.set_text_color(36, 37, 40)
        pdf.cell(130, 8, title)
        pdf.ln(8)
        img_path = OUT_DIR / f'{img_name}.png'
        pdf.image(str(img_path), x=x, y=28, w=130)
        img_h = 130 * (900 / 1440)  # misma relacion de aspecto
        pdf.set_xy(x, 32 + img_h)
        pdf.set_font('helvetica', '', 10)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(130, 5.5, desc)

    draw_block(10, *left)
    if right:
        draw_block(157, *right)

PDF_OUT.parent.mkdir(parents=True, exist_ok=True)
pdf.output(str(PDF_OUT))
print('PDF guardado en', PDF_OUT)
