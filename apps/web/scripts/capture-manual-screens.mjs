import { chromium, devices } from '@playwright/test'

const BASE = process.env.E2E_BASE_URL ?? 'http://localhost:5173'
const OUT = 'C:/Users/PC/Downloads/CRM-VENTAS/docs/manual/capturas'

const browser = await chromium.launch()
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-PE' })
const page = await context.newPage()

async function wait(ms = 900) {
  await page.waitForTimeout(ms)
}

async function shot(name) {
  await wait()
  await page.screenshot({ path: `${OUT}/${name}.png` })
  console.log('capturado', name)
}

async function go(path) {
  await page.goto(`${BASE}${path}`)
  await page.waitForLoadState('networkidle')
  await wait()
}

// Login
await page.goto(`${BASE}/login`)
await wait(700)
await shot('01-login')
await page.getByLabel('Correo').fill('admin@dataservice.pe')
await page.getByLabel('Contraseña', { exact: true }).fill('Admin123!')
await page.getByRole('button', { name: 'Ingresar' }).click()
await page.waitForURL(`${BASE}/`)
await wait(1000)

// 02 inicio
await go('/')
await shot('02-inicio')

// 03 prospectos
await go('/prospectos')
await shot('03-prospectos')

// Entrar al primer prospecto
await page.locator('table tbody tr').first().click()
await page.waitForURL(/\/prospectos\//)
await wait(1200)

// 04 detalle
await shot('04-prospecto-detalle')

// 05 interacciones
await page.getByRole('tab', { name: /Interacciones/ }).click()
await wait(1200)
await shot('05-prospecto-interacciones')

// 06 oportunidades
await page.getByRole('tab', { name: 'Oportunidades' }).click()
await wait(1200)
await shot('06-prospecto-oportunidades')

// 10 nueva oportunidad (desde la pestaña oportunidades)
await page.getByRole('button', { name: 'Nueva oportunidad' }).first().click()
await wait(1000)
await shot('10-nueva-oportunidad')
await page.keyboard.press('Escape')
await wait(400)

// 07 cotizaciones
await page.getByRole('tab', { name: 'Cotizaciones' }).click()
await wait(1200)
await shot('07-prospecto-cotizaciones')

// 13 nueva cotizacion
await page.getByRole('button', { name: 'Nueva cotización' }).first().click()
await wait(1000)
await shot('13-nueva-cotizacion')
await page.keyboard.press('Escape')
await wait(400)

// 08 nuevo prospecto
await go('/prospectos')
await page.getByRole('button', { name: 'Nuevo prospecto' }).first().click()
await wait(1000)
await shot('08-nuevo-prospecto')
await page.keyboard.press('Escape')
await wait(400)

// 09 pipeline
await go('/pipeline')
await shot('09-pipeline')

// 11 tareas
await go('/tareas')
await shot('11-tareas')

// 12 cotizaciones
await go('/cotizaciones')
await shot('12-cotizaciones')

// 14 informe semanal
await go('/informe-semanal')
await shot('14-informe-semanal')

// 15 alertas
await go('/alertas')
await shot('15-alertas')

// 16 productos
await go('/productos')
await shot('16-productos')

// 17 dashboard gerencial
await go('/dashboard/gerencial')
await shot('17-dashboard-gerencial')

// 18 usuarios
await go('/admin/usuarios')
await shot('18-usuarios')

// 19 roles
await go('/admin/roles')
await shot('19-roles')

// 20 catalogos
await go('/admin/catalogos')
await shot('20-catalogos')

// 21 configuracion
await go('/admin/configuracion')
await shot('21-configuracion')

// 22 auditoria
await go('/admin/auditoria')
await shot('22-auditoria')

await context.close()

// Movil
const mobile = await browser.newContext({ ...devices['Pixel 7'], locale: 'es-PE' })
const mpage = await mobile.newPage()
await mpage.goto(`${BASE}/login`)
await mpage.waitForTimeout(700)
await mpage.getByLabel('Correo').fill('admin@dataservice.pe')
await mpage.getByLabel('Contraseña', { exact: true }).fill('Admin123!')
await mpage.getByRole('button', { name: 'Ingresar' }).click()
await mpage.waitForURL(`${BASE}/`)
await mpage.waitForTimeout(1000)

await mpage.screenshot({ path: `${OUT}/23-movil.png` })
console.log('capturado 23-movil')

await mpage.goto(`${BASE}/prospectos`)
await mpage.waitForLoadState('networkidle')
await mpage.waitForTimeout(900)
await mpage.screenshot({ path: `${OUT}/24-movil-prospectos.png` })
console.log('capturado 24-movil-prospectos')

await mobile.close()
await browser.close()
console.log('Todas las capturas actualizadas en', OUT)
