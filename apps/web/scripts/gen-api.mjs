// Genera los tipos TypeScript del cliente a partir del OpenAPI del backend (sin levantar el servidor).
import { execFileSync } from 'node:child_process'
import { existsSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const apiDir = path.resolve(import.meta.dirname, '../../api')
const venvPython = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python'
const python = existsSync(path.join(apiDir, venvPython)) ? path.join(apiDir, venvPython) : 'python'
const spec = execFileSync(python, ['-m', 'scripts.export_openapi'], { cwd: apiDir, encoding: 'utf8' })
const specPath = path.resolve(import.meta.dirname, '../openapi.json')
writeFileSync(specPath, spec)
execFileSync('npx', ['openapi-typescript', specPath, '-o', 'src/shared/api/schema.d.ts'], {
  stdio: 'inherit',
  shell: true,
  cwd: path.resolve(import.meta.dirname, '..'),
})
