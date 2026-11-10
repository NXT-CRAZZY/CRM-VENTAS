import { chromium } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const repoRoot = resolve(dirname(__filename), '../../..')
const htmlPath = resolve(repoRoot, 'docs/manual/manual.html')
const pdfPath = resolve(repoRoot, 'docs/manual/Manual_Usuario_DSCONT_Ventas.pdf')

const browser = await chromium.launch()
const context = await browser.newContext()
const page = await context.newPage()

await page.goto('file:///' + htmlPath.replace(/\\/g, '/'))
await page.waitForLoadState('networkidle')
await page.waitForTimeout(1500)

await page.pdf({
  path: pdfPath,
  format: 'A4',
  printBackground: true,
  margin: { top: '0mm', right: '0mm', bottom: '0mm', left: '0mm' },
})

await browser.close()
console.log('PDF guardado en', pdfPath)
