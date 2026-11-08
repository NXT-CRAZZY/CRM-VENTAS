import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi } from 'vitest'

import AlertsPage from './AlertsPage'

const listMock = vi.fn()
const unreadCountMock = vi.fn()
const generateMock = vi.fn()
const markReadMock = vi.fn()
const dismissMock = vi.fn()

vi.mock('@/shared/auth/permissions', () => ({
  P: {},
  usePermissions: () => ({ can: () => false }),
}))

vi.mock('../api/alerts-service', () => ({
  alertsService: {
    list: (...args: unknown[]) => listMock(...args),
    unreadCount: () => unreadCountMock(),
    generate: () => generateMock(),
    markRead: (id: string) => markReadMock(id),
    dismiss: (id: string) => dismissMock(id),
  },
}))

function Wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('AlertsPage filters', () => {
  beforeEach(() => {
    listMock.mockResolvedValue({ items: [], total: 0 })
    unreadCountMock.mockResolvedValue(0)
  })

  it('calls list with status and severity filters', async () => {
    render(<AlertsPage />, { wrapper: Wrapper })

    // Estado inicial: Sin leer, Todas las severidades
    expect(listMock).toHaveBeenCalledWith(
      expect.objectContaining({ status: 'UNREAD', severity: undefined })
    )

    const user = userEvent.setup()

    // Cambiar a Leídas
    await user.click(screen.getByRole('tab', { name: 'Leídas' }))
    expect(listMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'READ', severity: undefined })
    )

    // Cambiar severidad a Crítica
    await user.click(screen.getByRole('tab', { name: 'Crítica' }))
    expect(listMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'READ', severity: 'CRITICAL' })
    )

    // Cambiar a Descartadas
    await user.click(screen.getByRole('tab', { name: 'Descartadas' }))
    expect(listMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'DISMISSED', severity: 'CRITICAL' })
    )
  })
})
