import { expect, type Page, test } from '@playwright/test'

const ADMIN = { email: 'admin@dataservice.pe', password: 'Admin123!' }
const SALES = { email: 'maria.quispe@dataservice.pe', password: 'Demo1234' }

async function login(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.getByLabel('Correo').fill(email)
  await page.getByLabel('Contraseña', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Ingresar' }).click()
}

async function openMenu(page: Page) {
  // En celular la navegación completa está en "Más".
  const more = page.getByRole('button', { name: 'Más' })
  if (await more.isVisible()) await more.click()
}

test('credenciales incorrectas muestran un mensaje claro', async ({ page }) => {
  await login(page, ADMIN.email, 'incorrecta')
  await expect(page.getByRole('alert')).toContainText('Correo o contraseña incorrectos')
})

test('la vendedora ve productos pero no la administración', async ({ page }) => {
  await login(page, SALES.email, SALES.password)
  await expect(page.getByRole('heading', { name: /María/ })).toBeVisible()
  await openMenu(page)
  await expect(page.getByRole('link', { name: 'Productos' }).first()).toBeVisible()
  await expect(page.getByRole('link', { name: 'Usuarios' })).toHaveCount(0)

  await page.goto('/admin/usuarios')
  await expect(page.getByText('Sin acceso')).toBeVisible()

  await page.goto('/productos')
  await expect(page.getByText('DS-CONT PERSONAL', { exact: true }).first()).toBeVisible()
})

test('el administrador crea una vendedora que define su contraseña al ingresar', async ({ page, browser }, info) => {
  const email = `e2e.${info.project.name}.${Date.now()}@dataservice.pe`

  await login(page, ADMIN.email, ADMIN.password)
  await page.goto('/admin/usuarios')
  await page.getByRole('button', { name: 'Nuevo usuario' }).first().click()

  const sheet = page.getByRole('dialog')
  await sheet.getByLabel('Nombre completo').fill('Vendedora E2E')
  await sheet.getByLabel('Correo').fill(email)
  await sheet.getByText('Ventas', { exact: true }).click()
  const tempPassword = await sheet.getByLabel('Contraseña temporal').inputValue()
  await sheet.getByRole('button', { name: 'Crear usuario' }).click()
  await expect(page.getByText(/Usuario Vendedora E2E creado/)).toBeVisible()

  // Nueva sesión, como la vendedora
  const context = await browser.newContext()
  const p2 = await context.newPage()
  await login(p2, email, tempPassword)
  await expect(p2.getByRole('heading', { name: 'Crea tu contraseña' })).toBeVisible()
  await p2.getByLabel('Contraseña actual').fill(tempPassword)
  await p2.getByLabel('Nueva contraseña').fill('MiClave2026')
  await p2.getByLabel('Repite la nueva contraseña').fill('MiClave2026')
  await p2.getByRole('button', { name: 'Guardar y continuar' }).click()
  await expect(p2.getByRole('heading', { name: /Vendedora/ })).toBeVisible()
  await context.close()
})

test('la sesión se mantiene al recargar la página', async ({ page }) => {
  await login(page, SALES.email, SALES.password)
  await expect(page.getByRole('heading', { name: /María/ })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: /María/ })).toBeVisible()
})
