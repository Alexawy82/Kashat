import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import Page from '../app/recurring/page'

const mockResponse = (data: unknown) =>
  ({ ok: true, text: async () => JSON.stringify(data) } as any)

const mockEmpty = () => ({ ok: true, text: async () => '' } as any)

describe('Recurring page', () => {
  beforeEach(() => {
    // @ts-ignore
    global.fetch = vi.fn(async (url: string) => {
      const urlString = url.toString()
      if (urlString.includes('/api/recurring/summary')) {
        return mockResponse({
          total_monthly: 120,
          essential_monthly: 80,
          discretionary_monthly: 40,
          total_annual: 1440,
        })
      }
      if (urlString.includes('/api/recurring/pending')) {
        return mockResponse([
          {
            id: 'p1',
            name: 'NETFLIX',
            cadence: 'monthly',
            amount_mean: 15.99,
            next_date: '2024-10-05',
            confidence: 0.9,
          },
        ])
      }
      if (urlString.includes('/api/recurring/confirmed')) {
        return mockResponse([
          {
            id: 'c1',
            display_name: 'Netflix',
            cadence: 'monthly',
            amount_mean: 15.99,
            next_date: '2024-10-05',
            status: 'active',
          },
        ])
      }
      if (urlString.includes('/api/recurring/subscriptions')) {
        return mockResponse([
          {
            id: 's1',
            display_name: 'Netflix',
            cadence: 'monthly',
            amount_mean: 15.99,
            next_date: '2024-10-05',
            status: 'active',
          },
        ])
      }
      if (urlString.includes('/api/recurring/bills')) return mockResponse([])
      if (urlString.includes('/api/recurring/loans')) return mockResponse([])
      if (urlString.includes('/api/recurring/credit-cards')) return mockResponse([])
      if (urlString.includes('/api/recurring/insurance')) return mockResponse([])
      if (urlString.includes('/api/recurring/insights/optimizations')) return mockResponse([])
      if (urlString.includes('/api/recurring/insights/cancellation-risks')) return mockResponse([])
      if (urlString.includes('/api/recurring/insights/upcoming')) return mockResponse([])
      if (urlString.includes('/api/recurring/insights')) return mockResponse([])
      if (urlString.includes('/api/recurring/insights/spending-by-type')) return mockResponse({ by_type: [] })
      return mockEmpty()
    })
  })

  it('renders summary and category tabs', async () => {
    render(<Page />)
    expect(await screen.findByText('Recurring Payments')).toBeInTheDocument()
    expect(await screen.findByText('Monthly Total')).toBeInTheDocument()
    expect(await screen.findByText('By Category')).toBeInTheDocument()
  })

  it('renders pending and confirmed items', async () => {
    render(<Page />)
    expect(await screen.findByText('Pending Review')).toBeInTheDocument()
    expect(await screen.findByText('NETFLIX')).toBeInTheDocument()
    expect(await screen.findByText('Netflix')).toBeInTheDocument()
  })
})
