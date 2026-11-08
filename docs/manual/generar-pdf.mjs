// Genera el PDF del manual a partir de manual.html usando Chrome/Edge instalado.
// Requiere Node 18+ y playwright-core:
//   npm i -D playwright-core
//   node generar-pdf.mjs
import { chromium } from 'playwright-core'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const html = path.join(here, 'manual.html')
const pdf = path.join(here, 'Manual_Usuario_CRM_DATA_SERVICE.pdf')

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const page = await browser.newPage()
await page.goto(pathToFileURL(html).href, { waitUntil: 'networkidle' })
await page.evaluate(async () => { await document.fonts.ready })
await page.waitForTimeout(800)

const footer = `
  <div style="width:100%;font-family:'Segoe UI',Arial,sans-serif;font-size:8px;color:#a1a1aa;padding:0 15mm;display:flex;justify-content:space-between;align-items:center;">
    <span>CRM DATA SERVICE · Manual de usuario</span>
    <span><span class="pageNumber"></span> / <span class="totalPages"></span></span>
  </div>`

await page.pdf({
  path: pdf,
  format: 'A4',
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: '<div></div>',
  footerTemplate: footer,
  margin: { top: '0mm', bottom: '12mm', left: '0mm', right: '0mm' },
})

console.log('PDF generado:', pdf)
await browser.close()
