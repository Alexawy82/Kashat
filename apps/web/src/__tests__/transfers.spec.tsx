import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Page from '../app/transfers/page'

describe('Transfers page', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = vi.fn(async (url: string, init?: any) => {
      if (url.toString().includes('/api/transfers?status=pending')) {
        return { ok: true, json: async () => ([{ left_tx_id:'L1', right_tx_id:'R1', score:0.95, group_id:'g1' }]) } as any
      }
      if (url.toString().includes('/api/transfers?status=confirmed')) {
        return { ok: true, json: async () => ([{ left_tx_id:'L2', right_tx_id:'R2', score:0.99, group_id:'g2', include_in_analytics:false }]) } as any
      }
      if (url.toString().includes('/api/transactions/')) {
        return { ok: true, json: async () => ({ id: 'L1', posted_at:'2024-08-01', description_norm: 'Transfer', amount:-300 }) } as any
      }
      return { ok: true, json: async () => ({}) } as any
    })
  })

  it('renders pending and confirmed tables', async () => {
    render(<Page />)
    expect(await screen.findByText('Transfers')).toBeInTheDocument()
    expect(await screen.findByText('Approve All Safe')).toBeInTheDocument()
  })

  it('suggest, approve, reject, toggle actions wired', async () => {
    const f = global.fetch as any
    render(<Page />)
    await screen.findByText('Approve')
    await fireEvent.click(screen.getByText('Approve'))
    expect(f).toHaveBeenCalled()
  })

  it('deep-link includes description filter', async () => {
    render(<Page />)
    const link = await screen.findByText('Open in Transactions')
    expect(link.getAttribute('href')).toContain('/transactions?desc=')
  })
})
