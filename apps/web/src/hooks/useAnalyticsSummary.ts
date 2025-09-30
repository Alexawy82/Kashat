'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { apiRequest } from '../utils/api'
import { UI_V1_COMPLETE } from '../utils/config'

export interface AnalyticsSummaryResult {
  totals: { income: number; spend: number; net: number }
  byMonth: Array<{ month: string; spend: number; income: number; net: number }>
  byCategory: Array<{ category_id?: string; category_name?: string; spend: number; count: number }>
  topMerchants: Array<{ merchant: string; spend: number; count: number }>
}

interface Params {
  from?: string
  to?: string
  includeTransfers?: boolean
}

export function useAnalyticsSummary(params: Params = {}) {
  const [data, setData] = useState<AnalyticsSummaryResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const cacheRef = useRef<Map<string, { t: number; v: AnalyticsSummaryResult }>>(new Map())

  const key = useMemo(() => JSON.stringify({ ...params, UI_V1_COMPLETE }), [params])

  useEffect(() => {
    let cancelled = false
    if (!UI_V1_COMPLETE) {
      // Feature flag off — do not fetch; consumer should degrade gracefully
      return
    }
    const cached = cacheRef.current.get(key)
    const now = Date.now()
    if (cached && now - cached.t < 120_000) {
      setData(cached.v)
      return
    }
    setLoading(true)
    setError(null)
    const qs = new URLSearchParams()
    if (params.from) qs.set('from', params.from)
    if (params.to) qs.set('to', params.to)
    if (params.includeTransfers) qs.set('includeTransfers', 'true')
    apiRequest<AnalyticsSummaryResult>(`/analytics/summary?${qs.toString()}`)
      .then((res) => {
        if (cancelled) return
        cacheRef.current.set(key, { t: Date.now(), v: res })
        setData(res)
      })
      .catch((e) => {
        if (cancelled) return
        setError(e?.message || 'Failed to load analytics summary')
      })
      .finally(() => !cancelled && setLoading(false))
    return () => { cancelled = true }
  }, [key])

  // expose invalidation
  const invalidate = () => {
    cacheRef.current.delete(key)
  }

  return { data, loading, error, invalidate, enabled: UI_V1_COMPLETE }
}

