# Manual de usuario · CRM DATA SERVICE

Documentación de uso del CRM comercial.

## Archivos

| Archivo | Descripción |
| --- | --- |
| `Manual_Usuario_CRM_DATA_SERVICE.pdf` | Manual listo para distribuir (A4, 23 páginas). |
| `manual.html` | Fuente del manual (HTML + CSS de impresión). |
| `generar-pdf.mjs` | Script que convierte el HTML en PDF con Chrome. |
| `capturas/` | Capturas reales del sistema con datos de demostración. |

## Regenerar el PDF

Requisitos: Node 18+ y Google Chrome instalado.

```bash
npm i -D playwright-core
node generar-pdf.mjs
```

El script abre `manual.html`, espera las fuentes y genera el PDF en la misma carpeta.

## Actualizar capturas

Las imágenes se tomaron del entorno de desarrollo (`http://localhost:5173`) con datos demo,
viewport 1440×900 y escala 2×. Si cambia la interfaz, reemplaza los archivos de `capturas/`
manteniendo los mismos nombres y vuelve a generar el PDF.

## Alcance

El manual cubre: acceso y seguridad, Inicio, Prospectos, Pipeline, Tareas, Cotizaciones,
Informe semanal, Alertas, Productos, Dashboard gerencial, Administración (usuarios, roles,
catálogos, configuración y auditoría), buenas prácticas, preguntas frecuentes y glosario.

El módulo de Importaciones está oculto en la aplicación y no forma parte del manual: el CRM
reemplaza el control en Excel y el formato FOR-VEN-001 se descarga desde **Informe semanal**.
