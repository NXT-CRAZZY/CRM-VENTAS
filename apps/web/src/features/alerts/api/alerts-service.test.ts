import { vi } from 'vitest'
import { alertsService } from './alerts-service'

describe('alertsService.list', () => {
  it('serializes status and severity as query params', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await alertsService.list({ status: 'UNREAD', severity: 'HIGH', page: 1, page_size: 20 })

    const request = fetchSpy.mock.calls[0][0] as Request
    const url = new URL(request.url)
    expect(url.searchParams.get('status')).toBe('UNREAD')
    expect(url.searchParams.get('severity')).toBe('HIGH')
    expect(url.searchParams.get('page')).toBe('1')
    expect(url.searchParams.get('page_size')).toBe('20')
  })

  it('omits ALL filters and sends only pagination', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ items: [], total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    await alertsService.list({ status: undefined, severity: undefined, page: 2, page_size: 20 })

    const request = fetchSpy.mock.calls[0][0] as Request
    const url = new URL(request.url)
    expect(url.searchParams.has('status')).toBe(false)
    expect(url.searchParams.has('severity')).toBe(false)
    expect(url.searchParams.get('page')).toBe('2')
  })
})
