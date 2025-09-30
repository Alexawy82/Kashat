"use client"
import { useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api'
const UI_V1 = (process.env.NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE === 'true' || process.env.NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE === '1')

export default function Page() {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [format, setFormat] = useState('csv')
  const [businessOnly, setBusinessOnly] = useState(false)
  const [includeTransfers, setIncludeTransfers] = useState(false)
  const [includeAdjustments, setIncludeAdjustments] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [history, setHistory] = useState<any[]>([])

  async function loadHistory() {
    try {
      const res = await fetch(`${API}/audit/logs?entity_type=export&action=export:csv&limit=5`)
      if (res.ok) {
        const data = await res.json()
        setHistory(data)
      }
    } catch {}
  }

  // lazy load on client interaction
  if (history.length === 0) {
    loadHistory()
  }

  async function handleQuickExport(exportType: 'all' | 'recent' | 'business') {
    setIsExporting(true)
    try {
      let url = `${API}/export/transactions.csv`
      
      if (exportType === 'recent') {
        const thirtyDaysAgo = new Date()
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
        url += `?start_date=${thirtyDaysAgo.toISOString().split('T')[0]}`
      }
      
      if (exportType === 'business') {
        url = `${API}/export?format=csv&business_only=true&include_transfers=false&include_adjustments=false`
      }
      
      if (exportType === 'business') {
        const response = await fetch(url, { method: 'POST' })
        const blob = await response.blob()
        downloadBlob(blob, 'business-transactions.csv')
      } else {
        // For GET requests, just open in new window to trigger download
        window.open(url, '_blank')
      }
    } finally {
      setIsExporting(false)
    }
  }

  async function handleAdvancedExport() {
    setIsExporting(true)
    try {
      if (UI_V1) {
        // New unified CSV export
        const qs = new URLSearchParams()
        if (startDate) qs.set('from', startDate)
        if (endDate) qs.set('to', endDate)
        if (businessOnly) qs.set('onlyBusiness', 'true')
        if (includeTransfers) qs.set('includeTransfers', 'true')
        const url = `${API}/export/csv?${qs.toString()}`
        window.open(url, '_blank')
        setTimeout(loadHistory, 1000)
      } else {
        const params = new URLSearchParams({
          format,
          business_only: businessOnly.toString(),
          include_transfers: includeTransfers.toString(),
          include_adjustments: includeAdjustments.toString()
        })
        let url = `${API}/export?${params.toString()}`
        if (startDate || endDate) {
          url = `${API}/export/transactions.csv`
          const dateParams = new URLSearchParams()
          if (startDate) dateParams.set('start_date', startDate)
          if (endDate) dateParams.set('end_date', endDate)
          url += `?${dateParams.toString()}`
          window.open(url, '_blank')
        } else {
          const response = await fetch(url, { method: 'POST' })
          const blob = await response.blob()
          const filename = `transactions-export.${format}`
          downloadBlob(blob, filename)
        }
      }
    } finally {
      setIsExporting(false)
    }
  }

  function downloadBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 32 }}>Export Data</h1>
      {UI_V1 && (
        <div style={{ marginBottom: 16, padding: '8px 12px', background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: 6 }}>
          New CSV export enabled. Recent exports are listed below.
        </div>
      )}

      {/* Quick Export Options */}
      <div style={{ background: '#fff', padding: 24, borderRadius: 8, border: '1px solid #e5e7eb', marginBottom: 24 }}>
        <h2 style={{ marginBottom: 16, fontSize: 18 }}>Quick Export</h2>
        <p style={{ marginBottom: 20, color: '#6b7280' }}>
          Export commonly requested data sets with one click.
        </p>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>📊 All Transactions</div>
            <div style={{ fontSize: 14, color: '#6b7280', marginBottom: 12 }}>Complete transaction history in CSV format</div>
            <button 
              onClick={() => handleQuickExport('all')} 
              disabled={isExporting}
              style={{ 
                width: '100%', 
                padding: '8px 16px', 
                background: '#3b82f6', 
                color: 'white', 
                border: 'none', 
                borderRadius: 6, 
                fontWeight: 500,
                opacity: isExporting ? 0.5 : 1,
                cursor: isExporting ? 'not-allowed' : 'pointer'
              }}
            >
              {isExporting ? 'Exporting...' : 'Export All'}
            </button>
          </div>

          <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>📅 Recent (30 days)</div>
            <div style={{ fontSize: 14, color: '#6b7280', marginBottom: 12 }}>Last 30 days of transactions</div>
            <button 
              onClick={() => handleQuickExport('recent')} 
              disabled={isExporting}
              style={{ 
                width: '100%', 
                padding: '8px 16px', 
                background: '#059669', 
                color: 'white', 
                border: 'none', 
                borderRadius: 6, 
                fontWeight: 500,
                opacity: isExporting ? 0.5 : 1,
                cursor: isExporting ? 'not-allowed' : 'pointer'
              }}
            >
              {isExporting ? 'Exporting...' : 'Export Recent'}
            </button>
          </div>

          <div style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>💼 Business Only</div>
            <div style={{ fontSize: 14, color: '#6b7280', marginBottom: 12 }}>Business transactions (no transfers/adjustments)</div>
            <button 
              onClick={() => handleQuickExport('business')} 
              disabled={isExporting}
              style={{ 
                width: '100%', 
                padding: '8px 16px', 
                background: '#dc2626', 
                color: 'white', 
                border: 'none', 
                borderRadius: 6, 
                fontWeight: 500,
                opacity: isExporting ? 0.5 : 1,
                cursor: isExporting ? 'not-allowed' : 'pointer'
              }}
            >
              {isExporting ? 'Exporting...' : 'Export Business'}
            </button>
          </div>
        </div>
      </div>

      {/* Advanced Export Options */}
      <div style={{ background: '#fff', padding: 24, borderRadius: 8, border: '1px solid #e5e7eb' }}>
        <h2 style={{ marginBottom: 16, fontSize: 18 }}>Advanced Export</h2>
        <p style={{ marginBottom: 20, color: '#6b7280' }}>
          Customize your export with specific date ranges and filtering options.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 24 }}>
          {/* Date Range */}
          <div style={{ background: '#f9fafb', padding: 16, borderRadius: 8 }}>
            <h3 style={{ marginBottom: 12, fontSize: 16 }}>Date Range</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 14, fontWeight: 500 }}>Start Date</label>
              <input 
                type="date" 
                value={startDate} 
                onChange={e => setStartDate(e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 14, fontWeight: 500 }}>End Date</label>
              <input 
                type="date" 
                value={endDate} 
                onChange={e => setEndDate(e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
              />
            </div>
          </div>

          {/* Format & Filters */}
          <div style={{ background: '#f9fafb', padding: 16, borderRadius: 8 }}>
            <h3 style={{ marginBottom: 12, fontSize: 16 }}>Format & Options</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'block', marginBottom: 6, fontSize: 14, fontWeight: 500 }}>Export Format</label>
              <select 
                value={format} 
                onChange={e => setFormat(e.target.value)}
                style={{ width: '100%', padding: 8, border: '1px solid #d1d5db', borderRadius: 4 }}
              >
                <option value="csv">CSV (Excel compatible)</option>
                <option value="parquet">Parquet (data analysis)</option>
              </select>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
                <input 
                  type="checkbox" 
                  checked={businessOnly} 
                  onChange={e => setBusinessOnly(e.target.checked)} 
                />
                Business transactions only
              </label>
              
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
                <input 
                  type="checkbox" 
                  checked={includeTransfers} 
                  onChange={e => setIncludeTransfers(e.target.checked)} 
                />
                Include transfers
              </label>
              
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}>
                <input 
                  type="checkbox" 
                  checked={includeAdjustments} 
                  onChange={e => setIncludeAdjustments(e.target.checked)} 
                />
                Include adjustments
              </label>
            </div>
          </div>
        </div>

        {/* Export Button */}
        <div style={{ textAlign: 'center' }}>
          <button 
            onClick={handleAdvancedExport}
            disabled={isExporting}
            style={{ 
              padding: '12px 32px', 
              background: '#3b82f6', 
              color: 'white', 
              border: 'none', 
              borderRadius: 6, 
              fontSize: 16, 
              fontWeight: 500,
              opacity: isExporting ? 0.5 : 1,
              cursor: isExporting ? 'not-allowed' : 'pointer'
            }}
          >
            {isExporting ? '🔄 Exporting...' : '📥 Export Custom Data'}
          </button>
        </div>
      </div>

      {UI_V1 && (
        <div style={{ marginTop: 24, background: '#fff', padding: 16, borderRadius: 8, border: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: 0, marginBottom: 8 }}>Export History</h3>
          {history.length === 0 ? (
            <div style={{ color: '#6b7280' }}>No recent exports.</div>
          ) : (
            <ul style={{ margin: 0, paddingLeft: 16 }}>
              {history.map((h, i) => (
                <li key={i} style={{ fontSize: 14 }}>
                  {new Date(h.ts).toLocaleString()} — {h.action}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Export Info */}
      <div style={{ marginTop: 24, padding: 16, background: '#f0f9ff', borderRadius: 8, border: '1px solid #e0f2fe' }}>
        <h3 style={{ marginBottom: 8, fontSize: 14, fontWeight: 600, color: '#0369a1' }}>📋 Export Details</h3>
        <div style={{ fontSize: 13, color: '#0369a1', lineHeight: 1.5 }}>
          <div><strong>CSV Format:</strong> Compatible with Excel, Google Sheets, and most accounting software</div>
          <div><strong>Parquet Format:</strong> Optimized for data analysis with pandas, R, or business intelligence tools</div>
          <div><strong>Transfers:</strong> Internal account-to-account movements (usually excluded from spending analysis)</div>
          <div><strong>Adjustments:</strong> Cashback, reversals, and corrections (may be excluded for clean reporting)</div>
        </div>
      </div>
    </div>
  )
}
