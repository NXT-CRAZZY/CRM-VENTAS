export type TaskTab = 'today' | 'upcoming' | 'overdue' | 'done'

/** Límites del día local: [inicio, fin). */
export function dayBounds(now = new Date()) {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const end = new Date(start.getTime() + 24 * 60 * 60 * 1000)
  return { start, end }
}

/** Pestaña de Tareas (Hoy / Próximas / Vencidas) en la que cae una tarea pendiente según su vencimiento. */
export function pendingTabFor(dueAt: string | null | undefined): Exclude<TaskTab, 'done'> {
  if (!dueAt) return 'upcoming'
  const due = new Date(dueAt)
  const { start, end } = dayBounds()
  if (due < start) return 'overdue'
  if (due < end) return 'today'
  return 'upcoming'
}
