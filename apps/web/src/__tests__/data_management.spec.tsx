import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Page from '../app/settings/data-management/page'

describe('Data Management page', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = vi.fn(async (url: string, init?: any) => {
      if (url.toString().endsWith('/api/imports/runs')) {
        return { ok: true, json: async () => ([{ id:'run1', started_at:'2024-09-01T00:00:00Z', files: 2, tx_count: 5, period_start:'2024-08-01', period_end:'2024-08-31' }]) } as any
      }
      if (url.toString().endsWith('/api/imports/runs/run1/files')) {
        return { ok: true, json: async () => ([{ path:'a.csv', type:'csv', tx_count:3 }]) } as any
      }
      if (url.toString().endsWith('/api/imports/runs/run1/summary')) {
        return { ok: true, json: async () => ([{ month:'2024-08-01', income:1000, spend:500, count: 10 }]) } as any
      }
      return { ok: true, json: async () => ({}) } as any
    })
    // Enable UI
    ;(process as any).env.NODE_ENV = 'development'
  })

  it('renders list, selects run, switches tabs', async () => {
    render(<Page />)
    expect(await screen.findByText('Data Management')).toBeInTheDocument()
  })

  it('triggers reprocess & delete with confirm', async () => {
    const f = global.fetch as any
    render(<Page />)
    // Select run
    const run = await screen.findByText(/2024/)
    fireEvent.click(run)
    // Mock confirm
    vi.spyOn(global, 'confirm' as any).mockReturnValue(true)
    const del = await screen.findByText('Delete')
    await fireEvent.click(del)
    expect(f).toHaveBeenCalled()
  })
})

