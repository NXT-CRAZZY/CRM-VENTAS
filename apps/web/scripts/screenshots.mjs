// Capturas de las pantallas principales en escritorio y celular (revisión visual del diseño).
// Requiere la app levantada con datos demo.  Uso: npm run screenshots
import { chromium, devices } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE = process.env.E2E_BASE_URL ?? 'http://localhost:5173'
const OUT = new URL('../../../docs/fase-0/capturas/', import.meta.url)
mkdirSync(OUT, { recursive: true })

const PAGES = [
  ['inicio', '/'],
  ['usuarios', '/admin/usuarios'],
  ['roles', '/admin/roles'],
  ['catalogos', '/admin/catalogos'],
  ['productos', '/productos'],
  ['configuracion', '/admin/configuracion'],
  ['auditoria', '/admin/auditoria'],
]

const browser = await chromium.launch()
for (const [device, options] of [
  ['escritorio', { viewport: { width: 1440, height: 900 } }],
  ['celular', devices['Pixel 7']],
]) {
  const context = await browser.newContext({ ...options, locale: 'es-PE', timezoneId: 'America/Lima' })
  const page = await context.newPage()
  await page.goto(`${BASE}/login`)
  await page.waitForTimeout(500)
  await page.screenshot({ path: new URL(`${device}-login.png`, OUT).pathname.slice(process.platform === 'win32' ? 1 : 0) })
  await page.getByLabel('Correo').fill('admin@dataservice.pe')
  await page.getByLabel('Contraseña', { exact: true }).fill('Admin123!')
  await page.getByRole('button', { name: 'Ingresar' }).click()
  await page.waitForURL(`${BASE}/`)
  for (const [name, path] of PAGES) {
    await page.goto(`${BASE}${path}`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(600)
    const file = new URL(`${device}-${name}.png`, OUT).pathname.slice(process.platform === 'win32' ? 1 : 0)
    await page.screenshot({ path: decodeURIComponent(file), fullPage: device === 'escritorio' })
  }
  await context.close()
}
await browser.close()
console.log('Capturas guardadas en docs/fase-0/capturas/')
